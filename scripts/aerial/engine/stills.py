"""Clean overlay stills (Kevin 2026-11-07, after three busy overlays): ONE line on the band, the aerial lightly tinted,
nothing else lit. A layout gets an overall still and a sheet of zooms (ZOOM_M square at ZOOM_SCALE x), every tile the
same single line, its station printed small in the corner.
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

TINT = 0.78               # the aerial's brightness under the line
LINE_RGB = (0, 235, 255)
ZOOM_M = 60.0
ZOOM_SCALE = 4
ZOOMS = 12


def _base(ortho):
    im = ortho.rgb * TINT
    return Image.fromarray(np.clip(im, 0, 255).astype(np.uint8))


def overall(ortho, C, path, width_px=3, max_side=2400):
    img = _base(ortho)
    px, py = ortho.en_to_px(C[:, 0], C[:, 1])
    pts = list(zip(px.tolist(), py.tolist()))
    d = ImageDraw.Draw(img)
    d.line(pts + pts[:1], fill=LINE_RGB, width=width_px)
    if max(img.size) > max_side:
        k = max_side / max(img.size)
        img = img.resize((int(img.width * k), int(img.height * k)), Image.LANCZOS)
    img.save(path, quality=90)


def zooms(ortho, C, s, path, n=ZOOMS, cols=4):
    """``n`` tiles evenly spaced in station along C (closed), ZOOM_M square, upsampled ZOOM_SCALE x."""
    gsd = float(np.mean(ortho.gsd))
    half_px = ZOOM_M / 2 / gsd
    base = _base(ortho)
    total = float(s[-1])
    tiles = []
    for q in np.linspace(0, total, n, endpoint=False):
        i = int(np.argmin(np.abs(s - q)))
        cx, cy = ortho.en_to_px(C[i, 0], C[i, 1])
        box = (int(cx - half_px), int(cy - half_px), int(cx + half_px), int(cy + half_px))
        t = base.crop(box).resize((int(2 * half_px * ZOOM_SCALE), int(2 * half_px * ZOOM_SCALE)), Image.BICUBIC)
        d = ImageDraw.Draw(t)
        px, py = ortho.en_to_px(C[:, 0], C[:, 1])
        sel = (np.abs(px - cx) < half_px * 1.5) & (np.abs(py - cy) < half_px * 1.5)
        seg = []
        for k in range(len(C)):
            if sel[k]:
                seg.append(((px[k] - box[0]) * ZOOM_SCALE, (py[k] - box[1]) * ZOOM_SCALE))
            elif seg:
                if len(seg) > 1:
                    d.line(seg, fill=LINE_RGB, width=2)
                seg = []
        if len(seg) > 1:
            d.line(seg, fill=LINE_RGB, width=2)
        d.text((6, 4), f"s {s[i]:.0f} m", fill=(255, 255, 255))
        tiles.append(t)
    w, h = tiles[0].size
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w + (cols - 1) * 4, rows * h + (rows - 1) * 4), (30, 30, 30))
    for k, t in enumerate(tiles):
        sheet.paste(t, ((k % cols) * (w + 4), (k // cols) * (h + 4)))
    if sheet.width > 2400:
        f = 2400 / sheet.width
        sheet = sheet.resize((2400, int(sheet.height * f)), Image.LANCZOS)
    sheet.save(path, quality=88)

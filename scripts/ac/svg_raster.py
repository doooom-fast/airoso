"""Rasterise the engine's own simple SVGs to PNG with Pillow — no qlmanage, no cairo, any OS.

Content Manager reads ``ui/<id>/preview.png`` and never an SVG. ``track_folder`` rasterised its
preview with macOS ``qlmanage`` and, anywhere else, left ``preview.svg`` behind: the Lake Murray V3
install (built on Windows) shipped no ``preview.png`` in any of its three ``ui/<id>/`` (ledger 0047
fix round, finding D). ``tools/pack_release.py`` already patched that over at pack time with a Pillow
polyline drawer; this is that drawer, shared, so the engine itself never leaves an SVG for CM.

It draws exactly what the engine writes — a background ``<rect>``, ``<polyline>`` strokes (the
track outline, ``track_folder._track_svg``), filled ``<polygon>`` triangles and ``<line>`` strokes
(``scripts/geometry/build_mesh`` ``track_render.svg``) — in document order; ``<text>`` is skipped.
It is not a general SVG renderer: an SVG with nothing it can draw returns False.
"""

from __future__ import annotations

import re
from pathlib import Path

_TAG = re.compile(r"<(rect|polyline|polygon|line)\b([^>]*)/?>", re.S)


def _attr(attrs: str, name: str) -> str | None:
    m = re.search(r'(?<![\w-])' + re.escape(name) + r'\s*=\s*"([^"]*)"', attrs)
    return m.group(1) if m else None


def _num(v: str | None, default: float) -> float:
    try:
        return float(re.match(r"\s*(-?[\d.]+)", v).group(1)) if v else default
    except (AttributeError, ValueError):
        return default


def _colour(v: str | None):
    if not v or v.strip().lower() in ("none", "transparent"):
        return None
    from PIL import ImageColor
    try:
        return ImageColor.getrgb(v.strip())
    except ValueError:
        return None


def _points(s: str) -> list[tuple[float, float]]:
    vals = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", s)]
    return list(zip(vals[0::2], vals[1::2]))


def rasterize_svg(svg: str, png: Path, size: int | None = None, aa: int = 2) -> bool:
    """Draw ``svg`` into ``png``. ``size``: the longer side in pixels (None = the SVG's own width/height).
    Drawn ``aa`` x larger and downsampled (LANCZOS) for antialiased strokes. Returns False — and writes
    nothing — when the SVG holds nothing this can draw."""
    from PIL import Image, ImageDraw
    head = re.search(r"<svg\b([^>]*)>", svg, re.S)
    if not head:
        return False
    ha = head.group(1)
    vb = _attr(ha, "viewBox")
    vbx = [float(x) for x in vb.replace(",", " ").split()] if vb else None
    w = _num(_attr(ha, "width"), vbx[2] if vbx else 0.0)
    h = _num(_attr(ha, "height"), vbx[3] if vbx else 0.0)
    if w <= 0 or h <= 0:
        return False
    ox, oy, sx, sy = 0.0, 0.0, 1.0, 1.0
    if vbx and vbx[2] > 0 and vbx[3] > 0:                       # user units -> the width/height box
        ox, oy, sx, sy = vbx[0], vbx[1], w / vbx[2], h / vbx[3]
    k = float(aa)

    def P(p):
        return ((p[0] - ox) * sx * k, (p[1] - oy) * sy * k)

    shapes = [(m.group(1), m.group(2)) for m in _TAG.finditer(svg)]
    if not any(t != "rect" for t, _ in shapes):
        return False
    im = Image.new("RGB", (max(1, round(w * k)), max(1, round(h * k))), (12, 17, 22))
    d = ImageDraw.Draw(im)
    for tag, a in shapes:
        if tag == "rect":
            fill = _colour(_attr(a, "fill"))
            if fill is not None:
                rw, rh = _attr(a, "width") or "100%", _attr(a, "height") or "100%"
                x0, y0 = _num(_attr(a, "x"), 0.0), _num(_attr(a, "y"), 0.0)
                x1 = w / sx + ox if rw.endswith("%") else x0 + _num(rw, 0.0)
                y1 = h / sy + oy if rh.endswith("%") else y0 + _num(rh, 0.0)
                d.rectangle([P((x0, y0)), P((x1, y1))], fill=fill)
            continue
        stroke = _colour(_attr(a, "stroke"))
        width = max(1, round(_num(_attr(a, "stroke-width"), 1.0) * sx * k))
        if tag == "line":
            pts = [(_num(_attr(a, "x1"), 0.0), _num(_attr(a, "y1"), 0.0)),
                   (_num(_attr(a, "x2"), 0.0), _num(_attr(a, "y2"), 0.0))]
        else:
            pts = _points(_attr(a, "points") or "")
        if len(pts) < 2:
            continue
        xy = [P(p) for p in pts]
        if tag == "polygon":
            fill = _colour(_attr(a, "fill") or "#000000")
            if fill is not None and len(xy) >= 3:
                d.polygon(xy, fill=fill, outline=stroke)
            elif stroke is not None:
                d.line(xy + [xy[0]], fill=stroke, width=width, joint="curve")
        elif stroke is not None or tag == "polyline":
            d.line(xy, fill=stroke or (255, 255, 255), width=width, joint="curve")
    tw, th = round(w), round(h)
    if size:
        f = size / max(w, h)
        tw, th = max(1, round(w * f)), max(1, round(h * f))
    im.resize((max(1, tw), max(1, th)), Image.LANCZOS).save(png, optimize=True)
    return True

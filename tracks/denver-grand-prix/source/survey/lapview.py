"""Crops of the cached aerials anywhere on the lap, in the survey's ENU frame, with what was read drawn on them.

    from lapview import View
    v = View(cache, 2022, (E0, N0, E1, N1), zoom=1.5)     # a crop mosaicked from the work tiles' PNGs (lap_fetch.py)
    v.xy(E, N)                                           # ENU metres -> crop pixels
    v.grid(10)                                           # labelled ENU ticks every 10 m, for reading a position by eye
    v.save(path)

All years share the archive's pixel grid (State Plane ft, 0.25 ft); a crop is cut on that grid, so nothing is resampled
before the final zoom. The image is NOT rotated: north is up within the grid convergence (about 0.3 degrees).
"""
import json, math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import lapgeo  # noqa: E402

PX = 0.25
_T = {}


def _tf():
    if not _T:
        from pyproj import Transformer
        _T['f'] = Transformer.from_crs(4326, 2232, always_xy=True); _T['i'] = Transformer.from_crs(2232, 4326, always_xy=True)
    return _T


def en_to_sp(E, N):
    lo, la = lapgeo.lonlat(E, N); return _tf()['f'].transform(lo, la)


def sp_to_en(X, Y):
    lo, la = _tf()['i'].transform(X, Y); return lapgeo.en(lo, la)


_IDX = {}


def index(cache, year):
    k = (cache, year)
    if k not in _IDX:
        d = os.path.join(cache, 'img', str(year)); out = []
        for t in lapgeo.tiles():
            p = os.path.join(d, t['id'] + '.json')
            if os.path.exists(p):
                out.append((t['id'], json.load(open(p))['bbox_ftus'], os.path.join(d, t['id'] + '.png')))
        _IDX[k] = out
    return _IDX[k]


class View:
    def __init__(self, cache, year, box, zoom=1.0):
        E0, N0, E1, N1 = box
        X, Y = en_to_sp([E0, E0, E1, E1], [N0, N1, N0, N1])
        self.X0 = math.floor(min(X) / PX) * PX + 0.125; self.Y1 = math.floor(max(Y) / PX) * PX + 0.125
        W = int(round((max(X) - self.X0) / PX)); H = int(round((self.Y1 - min(Y)) / PX))
        img = np.zeros((H, W, 3), np.uint8); self.covered = np.zeros((H, W), bool)
        for tid, bb, png in index(cache, year):
            if bb[0] >= self.X0 + W * PX or bb[2] <= self.X0 or bb[1] >= self.Y1 or bb[3] <= self.Y1 - H * PX:
                continue
            c0 = int(round((bb[0] - self.X0) / PX)); r0 = int(round((self.Y1 - bb[3]) / PX))
            a = np.asarray(Image.open(png).convert('RGB')); h, w = a.shape[:2]
            x0, x1 = max(0, c0), min(W, c0 + w); y0, y1 = max(0, r0), min(H, r0 + h)
            if x1 > x0 and y1 > y0:
                img[y0:y1, x0:x1] = a[y0 - r0:y1 - r0, x0 - c0:x1 - c0]; self.covered[y0:y1, x0:x1] = True
        self.raw = img; self.zoom = zoom; self.box = box; self.year = year
        self.im = Image.fromarray(img) if zoom == 1.0 else Image.fromarray(img).resize((int(W * zoom), int(H * zoom)), Image.LANCZOS if zoom < 1 else Image.BICUBIC)
        self.d = ImageDraw.Draw(self.im)
        try:
            self.font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 13)
        except Exception:           # noqa: BLE001
            self.font = ImageFont.load_default()

    def xy(self, E, N):
        X, Y = en_to_sp(E, N); x = (np.asarray(X) - self.X0) / PX - 0.5; y = (self.Y1 - np.asarray(Y)) / PX - 0.5
        return x * self.zoom, y * self.zoom

    def en(self, x, y):
        X = self.X0 + (np.asarray(x, float) / self.zoom + 0.5) * PX; Y = self.Y1 - (np.asarray(y, float) / self.zoom + 0.5) * PX
        return sp_to_en(X, Y)

    def line(self, pts, col, width=2):
        x, y = self.xy([p[0] for p in pts], [p[1] for p in pts]); self.d.line(list(zip(map(float, x), map(float, y))), fill=col, width=width)

    def ring(self, E, N, r, col, width=2):
        x, y = self.xy(E, N); x, y = float(x), float(y); self.d.ellipse([x - r, y - r, x + r, y + r], outline=col, width=width)

    def square(self, E, N, r, col, width=2):
        x, y = self.xy(E, N); x, y = float(x), float(y); self.d.rectangle([x - r, y - r, x + r, y + r], outline=col, width=width)

    def text(self, E, N, s, col=(255, 255, 0), dx=8, dy=-6):
        x, y = self.xy(E, N); x, y = float(x) + dx, float(y) + dy
        self.d.text((x + 1, y + 1), s, fill=(0, 0, 0), font=self.font); self.d.text((x, y), s, fill=col, font=self.font)

    def grid(self, step=10.0, col=(255, 255, 255)):
        E0, N0, E1, N1 = self.box
        for e in np.arange(math.ceil(E0 / step) * step, E1, step):
            x, _ = self.xy(e, N1); x = float(x); self.d.line([x, 0, x, 7], fill=col, width=1); self.d.line([x, self.im.height - 7, x, self.im.height], fill=col, width=1)
            self.d.text((x + 2, 1), f'{e:.0f}', fill=col, font=self.font)
        for n in np.arange(math.ceil(N0 / step) * step, N1, step):
            _, y = self.xy(E0, n); y = float(y); self.d.line([0, y, 7, y], fill=col, width=1); self.d.line([self.im.width - 7, y, self.im.width, y], fill=col, width=1)
            self.d.text((9, y - 7), f'{n:.0f}', fill=col, font=self.font)

    def save(self, path, quality=80):
        self.im.save(path, quality=quality)

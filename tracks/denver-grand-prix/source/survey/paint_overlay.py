"""Draw paint items on a crop of the aerial (the stills, and the overlays the refutation rounds were read from).

    from paint_overlay import draw
    v = draw(cache, items, box, year=2022, zoom=1.3)      # a lapview.View; v.save(path)

Colours: crosswalk bars green (inferred bars thin white-green), broken / dotted lines blue, solid white cyan, yellow lines
yellow, stop bars magenta, lone bars pink, typed symbols white label, untyped small marks orange rings, coloured surfaces
their outline in red / green. An item graded 'detected' is drawn one pixel thinner; one not seen in 2022 gets a red dot.
"""
import os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import lapgeo, lapview  # noqa: E402


def _en(pts):
    p = np.asarray(pts, float).reshape(-1, 2); E, N = lapgeo.en(p[:, 0], p[:, 1]); return list(zip(E, N))


def centre(it):
    for k in ('centre_lonlat',):
        if k in it:
            return _en(it[k])[0]
    for k in ('line_lonlat', 'outline_lonlat'):
        if k in it:
            p = np.array(_en(it[k])); return tuple(p.mean(0))
    if 'dashes_lonlat' in it:
        p = np.array(_en([q for d in it['dashes_lonlat'] for q in d])); return tuple(p.mean(0))
    return None


def draw(cache, items, box, year=2022, zoom=1.3, grid=10, labels=False):
    v = lapview.View(cache, year, box, zoom=zoom); E0, N0, E1, N1 = box
    for it in items:
        c = centre(it)
        if c is None or not (E0 - 30 <= c[0] <= E1 + 30 and N0 - 30 <= c[1] <= N1 + 30):
            continue
        w = 3 if it.get('grade') == 'measured' else 2; cl = it['class']
        if cl == 'crosswalk':
            for b in it['bars']:
                v.line(_en(b['ends_lonlat']), (190, 255, 190) if b.get('inferred') else (0, 255, 0), 1 if b.get('inferred') else w)
        elif cl == 'line' and 'dashes_lonlat' in it:
            for d in it['dashes_lonlat']:
                v.line(_en(d), (255, 220, 0) if it['colour'] == 'yellow' else (0, 140, 255), w)
        elif cl == 'line':
            v.line(_en(it['line_lonlat']), (255, 255, 0) if it['colour'] == 'yellow' else ((0, 255, 255) if it['pattern'] != 'single dash or fragment' else (0, 200, 200)), w if it['pattern'] != 'single dash or fragment' else 1)
        elif cl in ('stop_bar', 'bar'):
            v.line(_en(it['line_lonlat']), (255, 0, 255) if cl == 'stop_bar' else (255, 150, 200), w)
        elif cl == 'surface':
            p = _en(it['outline_lonlat']); v.line(p + [p[0]], (255, 60, 60) if it['colour'] == 'red' else (60, 255, 60), 2)
        elif cl == 'symbol':
            if it.get('type', 'untyped') == 'untyped':
                v.ring(c[0], c[1], 7, (255, 128, 0), 1)
            else:
                v.square(c[0], c[1], 9, (255, 255, 255), 2); v.text(c[0], c[1], it['type'], (255, 255, 255))
        if not it.get('seen', {}).get('2022', it.get('seen', {}).get(2022, 'seen')).startswith('seen'):
            x, y = v.xy(c[0], c[1]); v.d.ellipse([float(x) - 3, float(y) - 3, float(x) + 3, float(y) + 3], fill=(255, 0, 0))
        if labels:
            v.text(c[0], c[1], it['id'][1:].lstrip('0') or '0', (255, 255, 0))
    if grid:
        v.grid(grid)
    return v

"""One overlay still per leg: the paint inventory and the posts drawn on the 2022 picture (small JPEGs for SURVEY.md).

    python3 stills.py <cache-dir>          # reads paint.json, lamps.json, signals.json beside this file; writes stills/

The box is BOX_M square about the leg's busiest junction (the one with most paint items within the box), or the leg's middle
when it has none. Paint colours as paint_overlay.py; posts: yellow square = lamp, red square = signal mast, orange square =
signal post, white square = any other post; a post placed by eye only has a thin square.
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import lapgeo, paint_overlay as po  # noqa: E402

BOX_M = 64.0
COL = {'lamp': (255, 255, 0), 'signal_mast': (255, 40, 40), 'signal_post': (255, 150, 0)}


def posts():
    out = []
    for f in ('lamps.json', 'signals.json'):
        p = os.path.join(HERE, f)
        if os.path.exists(p):
            out += json.load(open(p))['posts']
    return out


def draw(cache, items, P, box, zoom=1.25, grid=10):
    v = po.draw(cache, items, box, zoom=zoom, grid=grid)
    for p in P:
        E, N = lapgeo.en(*p['lonlat'])
        if box[0] <= E <= box[2] and box[1] <= N <= box[3]:
            v.square(float(E), float(N), 8, COL.get(p['class'], (255, 255, 255)), 3 if p['grade'] == 'measured' else 1)
    return v


if __name__ == '__main__':
    cache = sys.argv[1]; items = json.load(open(os.path.join(HERE, 'paint.json')))['items']; P = posts(); L = lapgeo.lap(); J = lapgeo.junctions()
    C = np.array([po.centre(it) or (1e9, 1e9) for it in items]); os.makedirs(os.path.join(HERE, 'stills'), exist_ok=True); rows = []
    for k, name in enumerate(L['legs']):
        ss = L['s'][L['leg'] == k]; cands = [(float(np.mean([r['E'] for r in g])), float(np.mean([r['N'] for r in g]))) for g in J if ss.min() + 10 <= g[0]['s'] <= ss.max() - 10]
        mid = int(ss[len(ss) // 2]); cands.append((float(L['E'][mid]), float(L['N'][mid])))
        if lapgeo.COVERED_S[0] - 40 < ss.min() < lapgeo.COVERED_S[1]:
            cands = [c for c in cands if not (lapgeo.COVERED_S[0] - 20 <= lapgeo.where([c[0]], [c[1]])[0][0] <= lapgeo.COVERED_S[1] + 20)] or cands
        c = max(cands, key=lambda c: int(((np.abs(C[:, 0] - c[0]) < BOX_M / 2) & (np.abs(C[:, 1] - c[1]) < BOX_M / 2)).sum()))
        box = (c[0] - BOX_M / 2, c[1] - BOX_M / 2, c[0] + BOX_M / 2, c[1] + BOX_M / 2)
        f = 'leg%02d_%s.jpg' % (k + 1, name.lower().replace(' / ', '_').replace(' ', '_').replace('/', '_'))
        draw(cache, items, P, box).save(os.path.join(HERE, 'stills', f), quality=68); rows.append({'leg': name, 'file': 'stills/' + f, 'box_en': [round(b, 1) for b in box]}); print(f)
    json.dump(rows, open(os.path.join(HERE, 'stills', 'stills.json'), 'w'), indent=1)

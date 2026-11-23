"""Overlays for a refutation round: the paint inventory drawn on fresh boxes of the lap, and the item counts in each box.

    python3 refute.py <cache-dir> <paint.json> <out-dir> <round-name> j:<s>,... m:<s>,...

j: a junction (the box is centred on the OSM junction nearest that lap distance), m: a mid-block stretch (centred on the lap
line at that distance). Each box is BOX_M square. Writes <out-dir>/<round>_<k>_<j|m><s>.jpg and <round>_boxes.json (the items
in each box by class and grade: the denominators the round's precision and recall are counted against).
"""
import collections, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import lapgeo, paint_overlay as po  # noqa: E402

BOX_M = 46.0

if __name__ == '__main__':
    cache, pj, out, rnd = sys.argv[1:5]; items = json.load(open(pj))['items']; L = lapgeo.lap(); J = lapgeo.junctions(); os.makedirs(out, exist_ok=True); boxes = []
    cs = {it['id']: po.centre(it) for it in items}
    for arg in sys.argv[5:]:
        kind, ss = arg.split(':')
        for s in map(float, ss.split(',')):
            if kind == 'j':
                g = min(J, key=lambda g: abs(g[0]['s'] - s)); c = (float(np.mean([r['E'] for r in g])), float(np.mean([r['N'] for r in g]))); name = ' / '.join(sorted({n for r in g for n in r['lap_street'] + r['cross']}))
            else:
                k = int(s); c = (float(L['E'][k]), float(L['N'][k])); name = L['legs'][int(L['leg'][k])] + ' mid-block'
            box = (c[0] - BOX_M / 2, c[1] - BOX_M / 2, c[0] + BOX_M / 2, c[1] + BOX_M / 2)
            v = po.draw(cache, items, box, zoom=1.75, grid=5); f = f'{rnd}_{len(boxes):02d}_{kind}{int(s)}.jpg'; v.save(os.path.join(out, f), quality=86)
            inn = [it for it in items if cs[it['id']] and box[0] <= cs[it['id']][0] <= box[2] and box[1] <= cs[it['id']][1] <= box[3]]
            boxes.append({'k': len(boxes), 'file': f, 'kind': kind, 's_m': s, 'where': name, 'box_en': [round(b, 1) for b in box],
                          'items': dict(collections.Counter(f"{it['class']}{'/' + it.get('type', '') if it['class'] == 'symbol' else ''} {it['grade']}" for it in inn)), 'n_measured': sum(1 for it in inn if it['grade'] == 'measured'), 'n_detected': sum(1 for it in inn if it['grade'] == 'detected')})
            print(boxes[-1]['k'], f, name, boxes[-1]['n_measured'], boxes[-1]['n_detected'])
    json.dump(boxes, open(os.path.join(out, rnd + '_boxes.json'), 'w'), indent=1)

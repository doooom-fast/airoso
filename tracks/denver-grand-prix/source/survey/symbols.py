"""Typing the white symbols by shape (PLAN 4b: arrows, bike symbols, legends), and clearing the transient small marks.

Input: the tile stage's blobs (white connected shapes per flight year, long lines taken out) and the assembled items.
Each blob is turned into the frame of the OSM street it lies on (u along the way, v to its right), then:

  by exemplar   mask overlap (intersection over union, +-5 px shifts) with exemplars cut from this imagery and named by eye (exemplars/*.png, exemplars.json):
           the MUTCD lane-use TURN ARROW (left; its mirror image is the right-turn arrow: handedness is a property of the
           shape, whatever way it is turned). The blob is drawn in the street frame and tried in
           the four street-aligned orientations; accepted at EX_MIN with EX_MARGIN over the next best type; the heading is
           the orientation that won. OSM's turn:lanes is written beside each arrow and was NOT needed as a tiebreak.
           and the THROUGH ARROW. EX_MIN was set by eye on a gallery of every match at 0.5: every match at 0.77 or more was an
           arrow, none under 0.65 was; real arrows that scored 0.56-0.57 (worn, or cut by a shadow) therefore stay untyped.
           NOT typed, because the white reader does not hold them as shapes: the bicycle symbol and the BUS / ONLY legends (they lie on green and red panels). They stay
           untyped marks, or are absent; the panels themselves are 'surface' items.
  A typed symbol takes the small marks under it (its own pieces) out of the item list.

transient  an UNTYPED small mark (symbol, single dash or fragment) seen in one flight year only, where another year shows
           bare pavement, is dropped as transient (a vehicle's highlight, debris, a glint): paint stays between flights.
Thresholds [invented]; written into the output. What cannot be typed stays untyped.
"""
import collections, json, math, os, sys
import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import lapgeo  # noqa: E402

Q = {'EX_MIN': 0.7, 'EX_AREA': (0.6, 1.5), 'EX_MARGIN': 0.06, 'SAME_M': 0.8}
EXDIR = os.path.join(HERE, 'exemplars')


def unpack(b):
    return np.unpackbits(b['patch'], axis=1)[:, :b['patch_shape'][1]].astype(bool)


def uv(b, sb):
    """the blob's pixels in the street frame: u along bearing sb (m), v to the right of it"""
    pm = unpack(b); ys, xs = np.nonzero(pm); g = b['gsd']; x = (xs - xs.mean()) * g; y = -(ys - ys.mean()) * g
    a = math.radians(sb); return x * math.sin(a) + y * math.cos(a), x * math.cos(a) - y * math.sin(a)


def exemplars():
    p = os.path.join(EXDIR, 'exemplars.json')
    if not os.path.exists(p):
        return []
    from PIL import Image
    out = []
    for e in json.load(open(p))['exemplars']:
        m = np.asarray(Image.open(os.path.join(EXDIR, e['file'])).convert('L')) > 127; out.append((e['type'], m, e))
        if e['type'] == 'arrow_left':                      # the right-turn arrow is its mirror image
            out.append(('arrow_right', m[:, ::-1], e))
    return out


def raster(b, sb, size=64, m_per_px=0.0762):
    """the blob drawn in the street frame (u up), centred, on a fixed grid"""
    u, v = uv(b, sb); im = np.zeros((size, size), np.float32)
    r = np.round(size / 2 - u / m_per_px).astype(int); c = np.round(size / 2 + v / m_per_px).astype(int); ok = (r >= 0) & (r < size) & (c >= 0) & (c < size)
    im[r[ok], c[ok]] = 1.0; return ndimage.binary_closing(im > 0, iterations=1)


def ncc(a, e):
    """best overlap (intersection over union) of two masks, each dilated one pixel, over +-5 px shifts"""
    A = ndimage.binary_dilation(a); E = ndimage.binary_dilation(e); best = 0.0; ne = float(E.sum())
    for dy in range(-5, 6):
        for dx in range(-5, 6):
            S = np.roll(np.roll(A, dy, 0), dx, 1); i = float((S & E).sum()); best = max(best, i / (float(S.sum()) + ne - i + 1e-9))
    return best


def by_exemplar(b, sb, EX):
    if not EX:
        return None
    best = collections.defaultdict(float); rot = {}
    for k in range(4):
        im = raster(b, sb + 90.0 * k)
        for typ, m, e in EX:
            sc = ncc(im, m)
            if sc > best[typ]:
                best[typ] = sc; rot[typ] = (sb + 90.0 * k) % 360.0
    o = sorted(best.items(), key=lambda kv: -kv[1])
    if o[0][1] >= Q['EX_MIN'] and (len(o) == 1 or o[0][1] - o[1][1] >= Q['EX_MARGIN']):
        return o[0][0], rot[o[0][0]], {'score': round(o[0][1], 2), 'next': (o[1][0], round(o[1][1], 2)) if len(o) > 1 else None}
    return None


def type_blobs(blobs, st):
    st_tree, st_b, st_w = st; EX = exemplars(); out = []
    for b in blobs:
        if b['edge'] or not any(Q['EX_AREA'][0] * e['area_m2'] <= b['area'] <= Q['EX_AREA'][1] * e['area_m2'] for _, _, e in EX):
            continue
        d, k = st_tree.query(b['c']); w = st_w[k]; sb = float(st_b[k]); r = None; by = None
        if r is None:
            e = by_exemplar(b, sb, EX)
            if e:
                r = e; by = 'correlation with an exemplar named by eye'
        if r:
            if r[0].startswith('arrow'):
                r[2]['with_osm_oneway'] = (abs((r[1] - sb + 180) % 360 - 180) < 90) if w['tags'].get('oneway') == 'yes' else None
            out.append({'blob': b, 'type': r[0], 'heading': r[1], 'detail': r[2], 'typed_by': by, 'street': w['tags'].get('name', 'unnamed'), 'osm_way': w['id'], 'turn_lanes': w['tags'].get('turn:lanes')})
    return out


def type_all(items, blobs, st, cache):
    import pickle
    typed = type_blobs(blobs, st); counts = collections.Counter(); L = lapgeo.lap()
    # one symbol per place: join the years' typings of one shape
    typed.sort(key=lambda t: -t['blob']['year']); groups = []
    for t in typed:
        for g in groups:
            if np.hypot(*(t['blob']['c'] - g[0]['blob']['c'])) <= Q['SAME_M']:
                g.append(t); break
        else:
            groups.append([t])
    cov = pickle.load(open(os.path.join(cache, 'paint_cov.pkl'), 'rb'))['cov'] if os.path.exists(os.path.join(cache, 'paint_cov.pkl')) else {}
    ct = {y: cKDTree(np.stack([c['E'], c['N']], 1)) for y, c in cov.items()}
    new = []
    for g in groups:
        types = collections.Counter(t['type'] for t in g); typ = types.most_common(1)[0][0]; t0 = next(t for t in g if t['type'] == typ); b = t0['blob']; yrs = sorted({t['blob']['year'] for t in g if t['type'] == typ}, reverse=True)
        see = {}
        for y in (2022, 2020, 2018):
            if y in yrs:
                see[y] = 'seen'
            elif y in ct:
                d, i = ct[y].query(b['c']); see[y] = 'hidden' if (d < 1.5 and cov[y]['hid'][i] >= 0.3) else 'absent'
            else:
                see[y] = 'no picture'
        lo, la = lapgeo.lonlat(b['c'][0], b['c'][1]); x0, y0, x1, y1 = b['box_en']
        it = {'class': 'symbol', 'type': typ, 'colour': 'white', 'typed_by': t0['typed_by'], 'heading_deg': round(t0['heading'], 1), 'area_m2': round(b['area'], 2),
              'centre_lonlat': [round(float(lo), 7), round(float(la), 7)], 'street': t0['street'], 'osm_way': t0['osm_way'], 'osm_turn_lanes': t0['turn_lanes'], **t0['detail'],
              'types_by_year': {str(t['blob']['year']): t['type'] for t in g}, 'geometry_year': b['year'], 'seen': see, 'years_seen': yrs, 'lidar': 'unreadable', 'lidar_returns_on_it': 0,
              '_firm': len(types) == 1 or types[typ] >= 2, '_c': b['c'], '_box': (min(x0, x1) - 0.3, min(y0, y1) - 0.3, max(x0, x1) + 0.3, max(y0, y1) + 0.3)}
        new.append(it); counts[typ] += 1
    keep = []
    for it in items:
        c = it['_c']
        if it['class'] in ('symbol', 'bar') or (it['class'] == 'line' and it.get('pattern') == 'single dash or fragment'):
            if any(n['_box'][0] <= c[0] <= n['_box'][2] and n['_box'][1] <= c[1] <= n['_box'][3] for n in new):
                counts['pieces_taken_into_a_typed_symbol'] += 1; continue
            weak = it['class'] == 'symbol' or it['class'] == 'line'
            if weak and len(it['years_seen']) == 1 and it.get('in_shadow_2022') and it['years_seen'] == [2022]:
                counts['untyped_small_mark_read_only_under_the_2022_shadow_gain_dropped'] += 1; continue
            if weak and len(it['years_seen']) == 1 and any(v == 'absent' for v in it['seen'].values()):
                counts['untyped_small_mark_of_one_year_over_bare_pavement_in_another_dropped'] += 1; continue
        keep.append(it)
    for n in new:
        n.pop('_box')
    return keep + new, dict(counts)

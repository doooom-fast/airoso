"""The lap's paint inventory, assembled from the work tiles (stage 2; stage 1 is paint_tile.py).

    python3 paint_lap.py <cache-dir> [--out paint.json]

Everything here is geometry in ENU metres on marks the tile stage read; no pixel is looked at again except the symbol
shapes (symbols.py). Steps, each counted in the output:

  own       a mark belongs to the work tile whose 150 m cell holds its centre (tiles overlap by 24 m);
  roof      marks whose nearest lap point lies under the Convention Center (lapgeo.COVERED_S) are dropped: a roof's lines
            are not the street's. That stretch is declared unsurveyed;
  older     a 2020 / 2018 mark with no 2022 mark under it is kept only when it can carry weight: a thin mark where 2022 HAS paint
            that its reader rejected (a kerb or slab edge that one year's reader let through) is dropped; a fragment over bare
            2022 pavement is dropped (a vehicle's highlight, debris); a fragment hidden in 2022 is kept only if both older years
            show it. Firm older marks stay: hidden in 2022 they fill, over bare 2022 pavement they are flagged possibly removed;
  absorb    a fragment or small mark of one year lying inside a firm mark of another year is the same paint: dropped;
  lines     solid pieces end to end (gap <= JOIN_GAP_M, same direction) or overlapping (two tiles' views of one line, a
            line cut by a shadow's edge) become one line;
  crosswalk blocks side by side at one spacing; pieces of one row split by hidden bars are joined when the gap is a whole
            number of spacings, and each missing bar is written as inferred ONLY where the 2022 picture is hidden there
            (vehicle or shadow); a gap over visible pavement or an island stays a gap and the pieces stay apart;
  broken    dashes end to end on one line (nearest neighbour each way, mutual): dash and gap measured;
  role      longitudinal / transverse against the OSM street the mark lies on; a transverse bar at least STOP_L_MIN long
            that is not a crosswalk bar is a stop bar;
  symbols   symbols.py types the white blobs by shape; what it cannot type stays untyped;
  surfaces  red / green painted or paved surfaces seen in two flight years;
  grade     measured: a firm mark (crosswalk, line, broken line, stop bar, typed symbol, surface) seen in 2022, or hidden in
            2022 and seen in both 2020 and 2018. detected: everything else (fragments, untyped symbols, lone short bars, and
            any mark seen only in older years). A mark absent from a later year's visible pavement is flagged. A lone bar, stop
            bar or line that the 2020 lidar contradicts while the 2020 picture shows it is graded detected (the kerb's gutter
            pan reads as a bar; the laser tells concrete from paint).
  smooth    a solid line whose centre line leaves its own cubic fit by WANDER_RMS_M (rms) or WANDER_MAX_M is graded detected;
  lidar     per item: confirmed / contradicted / unreadable from the tile stage's intensity check (2020-05-27, another sensor).
"""
import collections, json, math, os, pickle, sys, time
import numpy as np
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import lapgeo  # noqa: E402

G = {'JOIN_GAP_M': 1.0, 'JOIN_DEG': 6.0, 'JOIN_LAT_M': 0.25, 'OVERLAP_M': 0.3, 'CW_DEG': 12.0, 'CW_GAP_MAX': 3.0, 'CW_MIN_BARS': 3, 'CW_JOIN_MAX_MISSING': 4,
     'CW_JOIN_FRAC': 0.3, 'DASH_DEG': 8.0, 'DASH_GAP': (0.5, 14.0), 'STOP_L_MIN': 2.0, 'TRANSVERSE_DEG': 30.0, 'FIRM_DASH_M': 1.5, 'SHORT_BAR_M': 1.5, 'WANDER_RMS_M': 0.12, 'WANDER_MAX_M': 0.35}
STD_LINE_IN = (4, 6, 8, 12); STD_BAR_IN = (12, 18, 24)


def adiff(a, b):
    return abs((a - b + 90.0) % 180.0 - 90.0)


def load(cache):
    marks = []; blobs = []; surfaces = []; stats = {}; cov = {}; shifts = {}; counts = collections.Counter(); sigma = None
    for t in lapgeo.tiles():
        p = os.path.join(cache, 'paint', t['id'] + '.pkl')
        if not os.path.exists(p):
            counts['tiles_missing'] += 1; continue
        d = pickle.load(open(p, 'rb')); x0, y0, x1, y1 = t['cell']; sigma = d['sigma_m']
        def mine(c):
            return x0 <= c[0] < x1 and y0 <= c[1] < y1
        for m in d['marks']:
            if mine(m['c']):
                m['tile'] = t['id']
                if m['year'] != 2022:                      # an older year's mark that 2022 does not hold: what earns it a place
                    st = str(m['seen'].get(2022)); weak = m['kind'] == 'symbol' or (m['kind'] in ('dash', 'block', 'bar') and m['L'] < G['FIRM_DASH_M'])
                    both = all(m['seen'].get(y) == 'seen' for y in (2020, 2018))
                    if st.startswith('rejected') and m['kind'] not in ('block', 'bar'):
                        counts['older_thin_mark_where_the_2022_reader_rejected_the_same_paint_dropped'] += 1; continue
                    if st == 'absent' and weak:
                        counts['older_fragment_over_bare_2022_pavement_dropped'] += 1; continue
                    if st == 'hidden' and weak and not both:
                        counts['older_fragment_of_one_year_hidden_in_2022_dropped'] += 1; continue
                marks.append(m)
        for b in d['blobs']:
            if mine(b['c']):
                b['tile'] = t['id']; blobs.append(b)
        for s in d['surfaces']:
            s['tile'] = t['id']; s['bbox_ftus'] = d.get('bbox_ftus'); surfaces.append(s)
        stats[t['id']] = d['stats']; shifts[t['id']] = d['shift_px']
        for k, v in d['counts'].items():
            counts['tile_' + k] += v
        for y, c in d['coverage'].items():
            inn = (c['E'] >= x0) & (c['E'] < x1) & (c['N'] >= y0) & (c['N'] < y1)
            cov.setdefault(y, []).append({k: (v[inn] if isinstance(v, np.ndarray) else v) for k, v in c.items()})
    cov = {y: {k: (np.concatenate([c[k] for c in v]) if k != 'cell_m2' else v[0][k]) for k in v[0]} for y, v in cov.items()}
    return marks, blobs, surfaces, stats, cov, shifts, counts, sigma


def streets():
    """samples every 2 m along every OSM street: position, bearing, the way"""
    o = lapgeo.osm(); P = []; B = []; Wy = []
    for w in o['ways']:
        if w['tags'].get('highway') in lapgeo.NON_STREET:
            continue
        ll = np.array([o['nodes'][str(n)] for n in w['nodes']]); E, N = lapgeo.en(ll[:, 0], ll[:, 1])
        for a in range(len(E) - 1):
            d = math.hypot(E[a + 1] - E[a], N[a + 1] - N[a]); n = max(1, int(d / 2.0))
            for k in range(n + 1):
                f = k / n; P.append((E[a] + f * (E[a + 1] - E[a]), N[a] + f * (N[a + 1] - N[a])))
                B.append(math.degrees(math.atan2(E[a + 1] - E[a], N[a + 1] - N[a])) % 360.0); Wy.append(w)
    return cKDTree(np.array(P)), np.array(B), Wy


class UF:
    def __init__(self, n):
        self.p = list(range(n))

    def f(self, a):
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]; a = self.p[a]
        return a

    def u(self, a, b):
        self.p[self.f(a)] = self.f(b)

    def groups(self):
        g = collections.defaultdict(list)
        for i in range(len(self.p)):
            g[self.f(i)].append(i)
        return list(g.values())


def seen_of(ms):
    out = {}
    for y in (2022, 2020, 2018):
        st = [str(m['seen'].get(y, 'no picture')) for m in ms]; c = collections.Counter(s.split(' ')[0] for s in st)
        n = len(st); see = c['seen'] + c['partly'] + c['rejected']
        out[y] = 'seen' if see >= 0.5 * n else ('hidden' if c['hidden'] + see >= 0.5 * n and c['hidden'] >= c['absent'] else ('no picture' if c['no'] == n else 'absent'))
        if out[y] == 'seen' and c['seen'] < 0.5 * n:
            out[y] = 'seen in part'
    return out


def lidar_of(ms):
    c = [m['lidar_confirms'] for m in ms if 'lidar_confirms' in m]
    if not c:
        return 'unreadable', sum(m.get('lidar_n', 0) for m in ms), ''
    return ('confirmed' if np.mean(c) >= 0.5 else 'contradicted'), sum(m.get('lidar_n', 0) for m in ms), f'{sum(c)} of {len(c)} parts'


def merge_line(ms):
    pts = np.concatenate([m['cl'] for m in ms]); c = pts.mean(0); q = pts - c; w, v = np.linalg.eigh(np.cov(q.T)); ax = v[:, 1]; t = q @ ax; o = np.argsort(t)
    pts = pts[o]; t = t[o]; keep = [0]
    for i in range(1, len(t)):                                   # thin the overlap of two views: one point per 0.25 m
        if t[i] - t[keep[-1]] >= 0.25:
            keep.append(i)
    cl = pts[keep]; Lw = np.array([m['L'] for m in ms]); m0 = max(ms, key=lambda m: m['L'])
    L = float(np.hypot(*np.diff(cl, axis=0).T).sum()) + 0.5 if len(cl) > 1 else float(Lw.max())
    out = dict(m0); out.update(c=cl.mean(0), ax=ax, cl=cl, ends=np.array([cl[0], cl[-1]]), L=max(L, float(Lw.max())), W=float(np.average([m['W'] for m in ms], weights=Lw)),
                               bearing=float(math.degrees(math.atan2(ax[0], ax[1])) % 180.0), parts=ms, kind='line' if max(L, Lw.max()) > 4.6 else m0['kind'],
                               double=bool(np.average([m['double'] for m in ms], weights=Lw) >= 0.5))
    return out


def assemble(cache):
    marks, blobs, surfaces, tstats, cov, shifts, counts, sigma = load(cache); counts['marks_from_tiles'] = len(marks)
    C = np.array([m['c'] for m in marks]); s, d, leg = lapgeo.where(C[:, 0], C[:, 1])
    keep = []
    for i, m in enumerate(marks):
        m['s'] = float(s[i]); m['leg'] = int(leg[i]); m['d'] = float(d[i])
        if lapgeo.COVERED_S[0] <= s[i] <= lapgeo.COVERED_S[1] and d[i] < 20.0:
            counts['dropped_under_the_roof'] += 1; continue
        keep.append(m)
    marks = keep
    # ---- absorb: a weak mark inside a firm mark of another year; a same-shape duplicate from another year
    firm = [i for i, m in enumerate(marks) if m['kind'] in ('line', 'block', 'bar') or (m['kind'] == 'dash' and m['L'] >= G['FIRM_DASH_M'])]
    C = np.array([m['c'] for m in marks]); tree = cKDTree(C); dead = set()
    for i in firm:
        a = marks[i]; nrm = np.array([-a['ax'][1], a['ax'][0]])
        for j in tree.query_ball_point(a['c'], a['L'] / 2 + 0.6):
            b = marks[j]
            if j == i or j in dead or i in dead or b['year'] == a['year']:
                continue
            dv = b['c'] - a['c']; al = abs(dv @ a['ax']); ac = abs(dv @ nrm)
            if al <= a['L'] / 2 + 0.25 and ac <= a['W'] / 2 + 0.25:
                weak = b['kind'] == 'symbol' or (b['kind'] == 'dash' and b['L'] < G['FIRM_DASH_M']) or b['L'] < 0.6 * a['L']
                same = b['kind'] == a['kind'] and adiff(a['bearing'], b['bearing']) < 10 and 0.7 < b['L'] / a['L'] < 1.4
                if weak and b['L'] < a['L']:
                    dead.add(j); counts['absorbed_fragment_inside_a_firm_mark'] += 1
                elif same:
                    lose = j if (a['year'] == 2022 or (b['year'] != 2022 and a['L'] >= b['L'])) else i
                    dead.add(lose); counts['absorbed_duplicate_of_another_year'] += 1
    marks = [m for i, m in enumerate(marks) if i not in dead]
    # ---- lines: end to end, or overlapping
    li = [i for i, m in enumerate(marks) if m['kind'] in ('line', 'dash')]; uf = UF(len(marks))
    ends = np.array([e for i in li for e in marks[i]['ends']]); own = np.array([i for i in li for _ in (0, 1)]); et = cKDTree(ends)
    for a, b in et.query_pairs(G['JOIN_GAP_M']):
        i, j = own[a], own[b]
        if i == j:
            continue
        A, B = marks[i], marks[j]
        if A['colour'] != B['colour'] or adiff(A['bearing'], B['bearing']) > G['JOIN_DEG']:
            continue
        if A['kind'] == 'dash' and B['kind'] == 'dash' and np.hypot(*(ends[a] - ends[b])) > 0.4:
            continue
        nrm = np.array([-A['ax'][1], A['ax'][0]])
        if abs((ends[b] - ends[a]) @ nrm) > G['JOIN_LAT_M'] or abs((B['c'] - A['c']) @ nrm) > G['JOIN_LAT_M'] + 0.02 * np.hypot(*(B['c'] - A['c'])):
            continue
        if abs((B['c'] - A['c']) @ A['ax']) < 0.5 * min(A['L'], B['L']):      # side by side, not end to end
            continue
        uf.u(i, j)
    lines = [i for i in li if marks[i]['kind'] == 'line']
    if lines:
        cp = np.concatenate([marks[i]['cl'] for i in lines]); co = np.concatenate([[i] * len(marks[i]['cl']) for i in lines]); ct = cKDTree(cp)
        for a, b in ct.query_pairs(G['OVERLAP_M']):
            i, j = co[a], co[b]
            if i != j and marks[i]['colour'] == marks[j]['colour'] and adiff(marks[i]['bearing'], marks[j]['bearing']) <= G['JOIN_DEG']:
                uf.u(i, j)
    out = []; used = set()
    for g in uf.groups():
        if len(g) > 1:
            out.append(merge_line([marks[i] for i in g])); used.update(g); counts['line_pieces_joined'] += len(g) - 1
    marks = [m for i, m in enumerate(marks) if i not in used] + out
    for m in marks:
        m.setdefault('parts', [m])
    # ---- crosswalks
    bl = [i for i, m in enumerate(marks) if m['kind'] == 'block']; uf = UF(len(marks))
    if bl:
        bt = cKDTree(np.array([marks[i]['c'] for i in bl]))
        for a, b in bt.query_pairs(G['CW_GAP_MAX'] + 2.0):
            A, B = marks[bl[a]], marks[bl[b]]; dv = B['c'] - A['c']; al = abs(dv @ A['ax']); ac = abs(dv @ np.array([-A['ax'][1], A['ax'][0]]))
            if adiff(A['bearing'], B['bearing']) < G['CW_DEG'] and 0.5 < ac <= G['CW_GAP_MAX'] and al <= 0.6 * max(A['L'], B['L']):
                uf.u(bl[a], bl[b])
    rows = [g for g in uf.groups() if marks[g[0]]['kind'] == 'block']
    def row_geom(g):
        ms = [marks[i] for i in g]; ax = ms[0]['ax'] * 1.0
        for m in ms:
            if m['ax'] @ ax < 0:
                m['ax'] = -m['ax']; m['ends'] = m['ends'][::-1]
        ax = np.mean([m['ax'] for m in ms], 0); ax /= np.hypot(*ax); nrm = np.array([-ax[1], ax[0]]); t = np.array([m['c'] @ nrm for m in ms]); o = np.argsort(t)
        sp = np.diff(t[o]); return [g[k] for k in o], ax, nrm, t[o], (float(np.median(sp)) if len(sp) else None)
    # join rows of one crosswalk: same direction, in line, a whole number of spacings apart
    R = [row_geom(g) for g in rows]; ru = UF(len(R))
    for a in range(len(R)):
        for b in range(a + 1, len(R)):
            ga, axa, na, ta, spa = R[a]; gb, axb, nb, tb, spb = R[b]
            sp = spa if (spa and len(ga) >= len(gb)) else (spb or spa)
            if not sp or (len(ga) < 2 and len(gb) < 2):
                continue
            ca = np.mean([marks[i]['c'] for i in ga], 0); cb = np.mean([marks[i]['c'] for i in gb], 0)
            if np.hypot(*(cb - ca)) > 40 or adiff(marks[ga[0]]['bearing'], marks[gb[0]]['bearing']) > G['CW_DEG']:
                continue
            La = np.median([marks[i]['L'] for i in ga + gb])
            if abs((cb - ca) @ axa) > 0.6 * La:
                continue
            tb2 = np.array([marks[i]['c'] @ na for i in gb]); gap = min(abs(tb2.min() - ta.max()), abs(ta.min() - tb2.max())) if (tb2.min() > ta.max() or tb2.max() < ta.min()) else 0.0
            k = gap / sp
            if 1.5 <= k <= G['CW_JOIN_MAX_MISSING'] + 1.5 and abs(k - round(k)) <= G['CW_JOIN_FRAC']:
                ru.u(a, b)
    cw = []
    for grp in ru.groups():
        g = [i for r in grp for i in R[r][0]]
        if len(g) >= G['CW_MIN_BARS']:
            cw.append((row_geom(g), len(grp)))
    cw_used = set(i for (g, *_), _ in cw for i in g)
    # ---- broken lines: mutual nearest dash each way
    ds = [i for i, m in enumerate(marks) if m['kind'] == 'dash' and i not in cw_used]; nxt = {}; prv = {}
    if ds:
        dt = cKDTree(np.array([marks[i]['c'] for i in ds]))
        def best(i, sign):
            A = marks[i]; nrm = np.array([-A['ax'][1], A['ax'][0]]); bj = None; bg = 1e9
            for q in dt.query_ball_point(A['c'], G['DASH_GAP'][1] + 6.0):
                j = ds[q]; B = marks[j]
                if j == i or B['colour'] != A['colour'] or adiff(A['bearing'], B['bearing']) > G['DASH_DEG']:
                    continue
                dv = B['c'] - A['c']; al = (dv @ A['ax']) * sign; ac = abs(dv @ nrm); gap = al - (A['L'] + B['L']) / 2
                if al > 0 and ac < 0.35 + 0.02 * al and G['DASH_GAP'][0] < gap < G['DASH_GAP'][1] and gap < bg:
                    bj, bg = j, gap
            return bj
        for i in ds:
            nxt[i] = best(i, +1); prv[i] = best(i, -1)
    du = UF(len(marks))
    for i in ds:
        for j in (nxt[i], prv[i]):
            if j is not None and i in (nxt.get(j), prv.get(j)):
                du.u(i, j)
    chains = [g for g in du.groups() if len(g) >= 2 and marks[g[0]]['kind'] == 'dash']
    ch_used = set(i for g in chains for i in g)
    left = [i for i in range(len(marks)) if i not in cw_used and i not in ch_used]
    return marks, cw, chains, left, blobs, surfaces, tstats, cov, shifts, counts, sigma


def cov_lookup(cov):
    c = cov.get(2022)
    if c is None:
        return lambda p: (0.0, 0.0)
    t = cKDTree(np.stack([c['E'], c['N']], 1))
    def f(p):
        d, i = t.query(p)
        return (float(c['road'][i]), float(c['hid'][i])) if d < 1.5 else (0.0, 0.0)
    return f


def ll(p):
    p = np.atleast_2d(np.asarray(p, float)); lo, la = lapgeo.lonlat(p[:, 0], p[:, 1])
    return [[round(float(a), 7), round(float(b), 7)] for a, b in zip(lo, la)]


def std(w, table):
    k = min(table, key=lambda v: abs(v * 0.0254 - w)); return k, round(k * 0.0254, 3)


def widths(ms, table):
    ms = [p for m in ms for p in m.get('parts', [m])]
    fit = [m['wfit'] for m in ms if 'wfit' in m and m.get('wrms', 99) < 0.25 * max(m.get('wcon', 1), 1)]; read = [m['W'] for m in ms]
    o = {'width_read_m': round(float(np.median(read)), 2)}
    if fit:
        w = float(np.median(fit)); k, km = std(w, table)
        o.update(width_m=round(w, 3), width_standard_in=k, width_standard_m=km, width_parts_fitted=len(fit))
    return o


def build(cache):
    marks, cw, chains, left, blobs, surfaces, tstats, cov, shifts, counts, sigma = assemble(cache)
    L = lapgeo.lap(); st_tree, st_b, st_w = streets(); hidden_at = cov_lookup(cov); items = []

    def base(ms, c):
        s, d, leg = lapgeo.where([c[0]], [c[1]]); dd, k = st_tree.query(c); w = st_w[k]
        parts = [p for m in ms for p in m.get('parts', [m])]; see = seen_of(parts); lv, ln, lp = lidar_of(parts)
        yrs = sorted({p['year'] for p in parts}, reverse=True)
        o = {'leg': L['legs'][int(leg[0])], 's_m': round(float(s[0]), 1), 'off_lap_m': round(float(d[0]), 1), 'street': w['tags'].get('name', 'unnamed'), 'osm_way': w['id'],
             'geometry_year': yrs[0] if len(yrs) == 1 else yrs, 'seen': see, 'years_seen': [y for y in (2022, 2020, 2018) if see[y].startswith('seen')],
             'in_shadow_2022': bool(np.mean([p['shadow'] for p in parts if p['year'] == 2022]) > 0.5) if any(p['year'] == 2022 for p in parts) else None,
             'lidar': lv, 'lidar_returns_on_it': int(ln)}
        if lp:
            o['lidar_parts_confirmed'] = lp
        return o, float(st_b[k])

    def role(bearing, sb):
        return 'transverse' if adiff(bearing, sb % 180.0) > 90 - G['TRANSVERSE_DEG'] else ('longitudinal' if adiff(bearing, sb % 180.0) < G['TRANSVERSE_DEG'] else 'oblique')

    for (g, ax, nrm, t, sp), npieces in cw:
        ms = [marks[i] for i in g]; Lb = float(np.median([m['L'] for m in ms])); bars = []; inferred = 0; gaps_left = 0
        for k, m in enumerate(ms):
            bars.append({'ends_lonlat': ll(m['ends']), 'year': m['year']})
            if k + 1 < len(ms) and sp:
                n = int(round((t[k + 1] - t[k]) / sp))
                if n >= 2 and abs((t[k + 1] - t[k]) / sp - n) <= G['CW_JOIN_FRAC'] + 0.1:
                    for q in range(1, n):
                        f = q / n; c = m['c'] * (1 - f) + ms[k + 1]['c'] * f; road, hid = hidden_at(c)
                        if road >= 0.5 and hid >= 0.3:
                            h = (m['ends'][1] - m['ends'][0]) * (1 - f) / 2 + (ms[k + 1]['ends'][1] - ms[k + 1]['ends'][0]) * f / 2
                            bars.append({'ends_lonlat': ll(np.array([c - h, c + h])), 'inferred': True, 'why': 'between read bars at the row\'s spacing; the 2022 picture is hidden here (vehicle or shadow) and no year shows it'}); inferred += 1
                        else:
                            gaps_left += 1
        c = np.mean([m['c'] for m in ms], 0); o, sb = base(ms, c); e = np.array([p for m in ms for p in m['ends']])
        ta, tb = (e @ ax).min(), (e @ ax).max(); na, nb = t.min() - ms[0]['W'] / 2, t.max() + ms[-1]['W'] / 2
        ring = np.array([ax * ta + nrm * na, ax * tb + nrm * na, ax * tb + nrm * nb, ax * ta + nrm * nb])
        items.append({'class': 'crosswalk', 'type': 'bars (continental)', 'colour': ms[0]['colour'], 'bars_read': len(ms), 'bars_inferred': inferred, 'pieces_joined': npieces,
                      'gaps_not_filled': gaps_left, 'bar_length_m': round(Lb, 2), 'bar_spacing_m': round(sp, 2) if sp else None, 'bar_bearing_deg': round(float(np.median([m['bearing'] for m in ms])), 1),
                      **{('bar_' + k): v for k, v in widths(ms, STD_BAR_IN).items()}, 'outline_lonlat': ll(ring), 'bars': bars, 'centre_lonlat': ll(c)[0], **o, '_firm': True, '_c': c})
    for g in chains:
        ms = [marks[i] for i in g]; ax0 = ms[0]['ax']; ms.sort(key=lambda m: float(m['c'] @ ax0)); gaps = []
        for a, b in zip(ms, ms[1:]):
            gaps.append(abs(float((b['c'] - a['c']) @ a['ax'])) - (a['L'] + b['L']) / 2)
        dl = float(np.median([m['L'] for m in ms])); c = np.mean([m['c'] for m in ms], 0); o, sb = base(ms, c); br = float(np.median([m['bearing'] for m in ms]))
        firm = len(ms) >= 3 or all(G['FIRM_DASH_M'] <= m['L'] for m in ms)
        items.append({'class': 'line', 'pattern': 'broken' if dl >= 1.5 else 'dotted', 'colour': ms[0]['colour'], 'dashes': len(ms), 'dash_m': round(dl, 2), 'gap_m': round(float(np.median(gaps)), 2),
                      'gap_max_m': round(float(max(gaps)), 2), 'length_m': round(float(np.hypot(*(ms[-1]['c'] - ms[0]['c']))) + dl, 1), 'bearing_deg': round(br, 1), 'role': role(br, sb),
                      **widths(ms, STD_LINE_IN), 'dashes_lonlat': [ll(m['ends']) for m in ms], 'dash_years': [m['year'] for m in ms], **o, '_firm': firm, '_c': c})
    for i in left:
        m = marks[i]; o, sb = base([m], m['c']); r = role(m['bearing'], sb)
        if m['kind'] in ('line', 'dash'):
            solid = m['kind'] == 'line'
            cl = m['cl'] if len(m['cl']) <= 40 else m['cl'][np.unique(np.round(np.linspace(0, len(m['cl']) - 1, max(40, int(m['L'] / 2)))).astype(int))]
            it = {'class': 'line', 'pattern': ('double solid' if m['double'] else 'solid') if solid else 'single dash or fragment', 'colour': m['colour'], 'length_m': round(m['L'], 1),
                  'bearing_deg': round(m['bearing'], 1), 'role': r, **widths([m], STD_LINE_IN), 'line_lonlat': ll(cl), **o, '_firm': solid, '_c': m['c']}
            if solid and len(m['cl']) >= 6:                 # paint is straight or smoothly curved: a cubic must follow it
                q = m['cl'] - m['cl'].mean(0); t = q @ m['ax']; u = q @ np.array([-m['ax'][1], m['ax'][0]])
                res = u - np.polyval(np.polyfit(t, u, 3), t); it['wander_rms_m'] = round(float(np.sqrt(np.mean(res ** 2))), 3)
                if it['wander_rms_m'] > G['WANDER_RMS_M'] or float(np.abs(res).max()) > G['WANDER_MAX_M']:
                    it['_firm'] = False; it['not_smooth'] = True
            if m['double']:
                it['width_note'] = 'a double line: width_m is the fitted box over both lines and the gap, not one line'; it.pop('width_standard_in', None); it.pop('width_standard_m', None)
            items.append(it)
        elif m['kind'] in ('bar', 'block'):
            stop = r == 'transverse' and m['L'] >= G['STOP_L_MIN']
            items.append({'class': 'stop_bar' if stop else 'bar', 'note': 'a transverse bar across the lanes, not part of a crosswalk row' if stop else 'a lone bar: a crosswalk bar with no neighbours read, a yield or gore piece',
                          'colour': m['colour'], 'length_m': round(m['L'], 1), 'bearing_deg': round(m['bearing'], 1), 'role': r, **widths([m], STD_BAR_IN), 'line_lonlat': ll(m['ends']), **o,
                          '_firm': m['L'] >= G['SHORT_BAR_M'], '_c': m['c']})
        else:
            items.append({'class': 'symbol', 'type': 'untyped', 'note': 'a small mark: part of an arrow or legend, a worn piece, or clutter', 'colour': m['colour'], 'area_m2': round(m['area'], 2),
                          'length_m': round(m['L'], 1), 'width_read_m': round(m['W'], 2), 'bearing_deg': round(m['bearing'], 1), 'centre_lonlat': ll(m['c'])[0], **o, '_firm': False, '_c': m['c'], '_mark': m})
    return items, marks, blobs, surfaces, tstats, cov, shifts, counts, sigma, (st_tree, st_b, st_w)


def grade(it):
    see = it['seen']; s22 = see[2022].startswith('seen'); older = [y for y in (2020, 2018) if see[y].startswith('seen')]
    flags = []
    if not s22:
        if see[2022] == 'absent':
            flags.append('possibly removed: seen in ' + ', '.join(map(str, older)) + ', and the 2022 picture shows bare pavement there')
        else:
            flags.append('not seen in 2022 (hidden there by a vehicle or shadow); read from ' + ', '.join(map(str, older)))
    else:
        for y in (2020, 2018):
            if see[y] == 'absent':
                flags.append(f'absent in {y} (pavement visible, no paint): painted since')
    if it.pop('not_smooth', False):
        flags.append('wanders off any smooth curve (a seam, a kerb, a shadow\'s stepped edge is likely): graded detected')
    n = len(it['years_seen'])
    firm = it.pop('_firm')
    if firm and it['class'] in ('bar', 'stop_bar', 'line') and it.get('lidar') == 'contradicted' and see[2020].startswith('seen'):
        firm = False; flags.append('the 2020 lidar contradicts it although the 2020 picture shows it too: a kerb, gutter or slab edge is likely; graded detected')
    if firm and (s22 or (len(older) == 2 and see[2022] != 'absent')):
        it['grade'] = 'measured'
    else:
        it['grade'] = 'detected'
    it['strength'] = {3: 'three flight years', 2: 'two flight years', 1: 'one flight year'}.get(n, 'one flight year')
    if flags:
        it['flags'] = flags
    return it


def finish(cache, outp, items, counts, sym_counts, sigma, shifts, tstats, cov):
    import paint_read as pr, paint_tile as pt, prep, symbols, surfaces as surf
    L = lapgeo.lap(); o = lapgeo.osm(); W = {w['id']: w for w in o['ways']}
    # what could not be read: per 1 m cell of roadway, per year; and in no year
    yrs = sorted(cov, reverse=True); c0 = cov[2022]; s, d, leg = lapgeo.where(c0['E'], c0['N'])
    road = np.max([cov[y]['road'] for y in yrs if len(cov[y]['road']) == len(c0['road'])], 0) > 0.5
    hid_all = np.all([(cov[y]['hid'] >= 0.5 * np.maximum(cov[y]['road'], 1e-3)) | (cov[y]['road'] < 0.5) for y in yrs if len(cov[y]['road']) == len(c0['road'])], 0) & road
    under_roof = (s >= lapgeo.COVERED_S[0]) & (s <= lapgeo.COVERED_S[1]) & (d < 20)
    legs = []
    for k, name in enumerate(L['legs']):
        m = (leg == k) & ~under_roof; its = [it for it in items if it['leg'] == name]; meas = [it for it in its if it['grade'] == 'measured']
        row = {'leg': name, 'lap_m': int((L['leg'] == k).sum()), 'items': len(its), 'measured': len(meas), 'detected': len(its) - len(meas),
               'by_class': dict(collections.Counter(it['class'] for it in its)),
               'lidar_check_of_measured': dict(collections.Counter(it['lidar'] for it in meas if it['class'] != 'surface' and it['class'] != 'symbol')),
               'roadway_m2': {str(y): int(cov[y]['road'][m].sum() * cov[y]['cell_m2']) for y in yrs},
               'hidden_share': {str(y): {'vehicles': round(float(cov[y]['veh'][m].sum() / max(cov[y]['road'][m].sum(), 1)), 3), 'building_shadow_read_with_gain': round(float(cov[y]['shadow'][m].sum() / max(cov[y]['road'][m].sum(), 1)), 3)} for y in yrs},
               'roadway_hidden_in_every_year_m2': int(hid_all[m].sum() * c0['cell_m2']), 'roadway_hidden_in_every_year_share': round(float(hid_all[m].sum() / max(road[m].sum(), 1)), 3)}
        legs.append(row)
    meas = [it for it in items if it['grade'] == 'measured']
    lw = [it for it in items if it['class'] == 'line' and it.get('pattern') in ('solid', 'broken') and 'width_m' in it and it['grade'] == 'measured' and it['colour'] == 'white']
    def pct(v):
        return [round(float(x), 3) for x in np.percentile(v, [16, 50, 84])] if len(v) else None
    colfax = []
    for g in json.load(open(os.path.join(lapgeo.T, 'data', 'lap_ways.plan.json')))['legs']:
        for wid in g['ways']:
            t = W[wid]['tags']
            if 'Colfax' in t.get('name', ''):
                colfax.append({'osm_way': wid, 'name': t.get('name'), **{k: t[k] for k in ('lanes', 'bus:lanes', 'access:lanes', 'turn:lanes', 'cycleway:right', 'maxspeed') if k in t}})
    doc = {'_doc': 'Road paint on the Denver Grand Prix lap corridor (PLAN 4b), read off DRCOG\'s 3-inch aerials of 2022, 2020 and 2018 by paint_tile.py and assembled by '
                   'paint_lap.py. Positions are lon / lat as the 2022 picture\'s georeference gives them (EPSG:2232 inferred; no registration shift applied; the older years '
                   'are moved onto 2022 by the per-tile shift measured from their paint). The state surveyed is 2022\'s (PLAN D8). Every item is a mark a picture shows, '
                   'except crosswalk bars flagged inferred. grade: measured / detected as SURVEY.md defines them; nothing is tagged or invented. See SURVEY.md.',
           'written_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
           'sources': {'aerials': 'https://drapparchive.s3.amazonaws.com/<year>/<tile>.tif, years 2022, 2020, 2018, 0.25 ft pixels, read by HTTP range (lap_fetch.py)',
                       'lidar': 'USGS 3DEP CO_DRCOG_2_2020 (EPT), flown 2020-05-27: the intensity check only', 'osm': o.get('osm_base')},
           'frame': {'origin_lonlat': list(lapgeo.ORIGIN), 'corridor_half_width_m': lapgeo.CORRIDOR_M, 'lap_m': round(L['length'], 1)},
           'unsurveyed': [{'what': 'Stout St under the Colorado Convention Center', 's_m': list(lapgeo.COVERED_S), 'length_m': lapgeo.COVERED_S[1] - lapgeo.COVERED_S[0],
                           'why': 'covered (OSM tunnel=building_passage): no aerial sees the road; nothing is filled in', 'marks_dropped_there': counts.get('dropped_under_the_roof', 0)}],
           'colfax': {'surveyed_state': 2022, 'note': 'PLAN D8: the last state a survey saw finished. OSM\'s present tags on the lap\'s Colfax ways are below: changed since, NOT surveyed; no paint is guessed from them.',
                      'osm_present_tags': colfax},
           'thresholds_invented': {'paint_read': pr.P, 'paint_tile': pt.Q, 'prep': prep.Q, 'paint_lap': G, 'symbols': symbols.Q, 'surfaces': surf.Q},
           'point_spread_sigma_m': sigma,
           'year_to_2022_shift_px': {str(y): dict(collections.Counter(f"{v[y]['dx']},{v[y]['dy']}" for v in shifts.values() if y in v)) for y in (2020, 2018)},
           'counts': {'items': len(items), 'by_class': dict(collections.Counter(it['class'] for it in items)), 'by_class_and_grade': {f"{c} / {g}": n for (c, g), n in sorted(collections.Counter((it['class'], it['grade']) for it in items).items())},
                      'line_patterns': dict(collections.Counter(it.get('pattern') for it in items if it['class'] == 'line')), 'symbol_types': dict(collections.Counter(it.get('type') for it in items if it['class'] == 'symbol')),
                      'crosswalk_bars_read': sum(it['bars_read'] for it in items if it['class'] == 'crosswalk'), 'crosswalk_bars_inferred': sum(it['bars_inferred'] for it in items if it['class'] == 'crosswalk'),
                      'crosswalks_joined_from_pieces': sum(1 for it in items if it['class'] == 'crosswalk' and it['pieces_joined'] > 1), 'assembly': dict(counts), 'symbol_typing': sym_counts},
           'grade_shares': {g: round(sum(1 for it in items if it['grade'] == g) / max(len(items), 1), 3) for g in ('measured', 'detected')},
           'strength_of_measured': dict(collections.Counter(it['strength'] for it in meas)),
           'not_seen_in_2022': {'filled_from_older_years_hidden_in_2022': sum(1 for it in items if any(f.startswith('not seen in 2022') for f in it.get('flags', []))),
                                'possibly_removed': sum(1 for it in items if any(f.startswith('possibly removed') for f in it.get('flags', [])))},
           'lidar_check_of_measured': dict(collections.Counter(it['lidar'] for it in meas if it['class'] not in ('surface', 'symbol'))),
           'widths': {'white_lane_lines_fitted_m_p16_p50_p84': pct([it['width_m'] for it in lw]), 'white_lane_lines_read_m_p16_p50_p84': pct([it['width_read_m'] for it in lw]),
                      'white_lane_lines_nearest_standard_in': dict(collections.Counter(it['width_standard_in'] for it in lw)),
                      'crosswalk_bar_fitted_m_p16_p50_p84': pct([it['bar_width_m'] for it in items if it['class'] == 'crosswalk' and 'bar_width_m' in it]),
                      'crosswalk_bar_read_m_p16_p50_p84': pct([it['bar_width_read_m'] for it in items if it['class'] == 'crosswalk']),
                      'stop_bar_fitted_m_p16_p50_p84': pct([it['width_m'] for it in items if it['class'] == 'stop_bar' and 'width_m' in it])},
           'per_leg': legs, 'items': items}
    with open(outp, 'w') as f:
        head = {k: v for k, v in doc.items() if k != 'items'}; txt = json.dumps(head, indent=1, default=float)
        f.write(txt[:-2] + ',\n "items": [\n' + ',\n'.join(json.dumps(it, default=float, separators=(',', ':')) for it in items) + '\n ]\n}\n')
    print('wrote', outp, os.path.getsize(outp) // 1000, 'kB;', doc['counts']['by_class_and_grade'], doc['lidar_check_of_measured'], doc['widths'])


if __name__ == '__main__':
    import symbols, surfaces as surf
    a = sys.argv; cache = a[1]; outp = a[a.index('--out') + 1] if '--out' in a else os.path.join(HERE, 'paint.json')
    items, marks, blobs, surfaces, tstats, cov, shifts, counts, sigma, st = build(cache)
    items, sym_counts = symbols.type_all(items, blobs, st, cache)
    items += surf.items(surfaces, cache)
    L = lapgeo.lap()
    for it in items:
        if 'leg' not in it:
            s, d, leg = lapgeo.where([it['_c'][0]], [it['_c'][1]]); it.update(leg=L['legs'][int(leg[0])], s_m=round(float(s[0]), 1), off_lap_m=round(float(d[0]), 1))
    items = [it for it in items if not (lapgeo.COVERED_S[0] <= it['s_m'] <= lapgeo.COVERED_S[1] and it['off_lap_m'] < 20)]
    items.sort(key=lambda it: (it['s_m'], it['class']))
    for k, it in enumerate(items):
        grade(it); it.pop('_c', None); it.pop('_mark', None); it['id'] = f'p{k:05d}'
    json.dump({'items': items, 'counts': dict(counts), 'symbols': sym_counts, 'sigma': sigma, 'shifts': {t: {str(y): v for y, v in s.items()} for t, s in shifts.items()}},
              open(os.path.join(cache, 'paint_raw.json'), 'w'), default=float)
    pickle.dump({'tstats': tstats, 'cov': cov}, open(os.path.join(cache, 'paint_cov.pkl'), 'wb'))
    finish(cache, outp, items, counts, sym_counts, sigma, shifts, tstats, cov)
    print(len(items), 'items', collections.Counter((it['class'], it['grade']) for it in items)); print(dict(counts)); print(sym_counts)

"""The lap's posts: the years' shadow strokes joined into candidates, the panels the eye reads, and the inventory.

    python3 posts_lap.py cluster <cache-dir>     # candidates (cache/posts_candidates.json) + panels (cache/panels/*.jpg, panels.json)
    python3 posts_lap.py cluster2 <cache-dir>    # second pass: new candidates only (cache/posts_candidates_r2.json, panels_r2/)
    python3 posts_lap.py apply   <cache-dir>     # verdicts (eye/verdicts_*.json beside this file) -> lamps.json, signals.json

cluster  Every stroke of every year (posts_tile.py) whose base lies within POST_CORRIDOR_M of the lap, not under the roof.
         Bases within JOIN_M of each other are one candidate. The flight years have different sun bearings (2022 and 2018
         about north, 2020 north-west), so strokes of two years that START at one point are an upright thing standing
         there: that is the independent reading, and 'spread_m' (the largest distance between the years' bases) is its
         position check. The reader's verdict, before any eye:
           post      two or three years' strokes share the foot, and it does not look like a tree;
           tree?     the far end of the shadow runs into a tangle (tip_mass over TREE_TIP_M2) in most years;
           one-year  one year only, and the other years could not have shown it (a building's shadow at the foot);
         dropped and counted: one year only where another year shows sunlit ground with no stroke (a person, a vehicle's
         edge, a shadow of something gone); one-year strokes with the base inside the roadway; strokes in a crowd (a fence).
panels   The lap cut into PANEL_STEP_M steps; each panel shows 2022 (left) and 2020 (right) at the picture's own resolution
         with every candidate ringed and numbered. The eye gives each number a class and adds what the reader missed
         (eye/README.md is the brief the readers worked from). Every candidate is judged in exactly one panel.
apply    Writes lamps.json (lamps and every other post that is not a signal) and signals.json (signal masts, pedestrian
         signal posts, and the count per OSM signal node and per junction, zero included).
"""
import collections, glob, json, math, os, pickle, sys, time
import numpy as np
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import lapgeo  # noqa: E402

Q = {'POST_CORRIDOR_M': 25.0, 'JOIN_M': 0.9, 'TREE_TIP_M2': 2.5, 'CROWD_R_M': 2.0, 'CROWD_N': 3, 'SHADOW_MIN_M': 1.2, 'PANEL_STEP_M': 48.0, 'PANEL_M': 58.0,
     'EYE_SNAP_M': 1.0, 'R2_OLD_M': 1.0, 'R2_POST_M': 1.6, 'EYE_DEDUPE_M': 1.6, 'SIGNAL_JUNCTION_R_M': 32.0}
YEARS = (2022, 2020, 2018)
CLASSES = ['lamp', 'signal_mast', 'signal_post', 'sign_or_small_post', 'utility_pole', 'post_unknown', 'not_a_post', 'cannot_tell']


def cluster(cache, save=True):
    S = []; grids = {y: [] for y in YEARS}; sun = {}
    for t in lapgeo.tiles():
        p = os.path.join(cache, 'posts', t['id'] + '.pkl')
        if not os.path.exists(p):
            continue
        d = pickle.load(open(p, 'rb')); x0, y0, x1, y1 = t['cell']
        for y, v in d['years'].items():
            sun.setdefault(y, {})[t['id']] = (v['sun_shadow_bearing_deg'], v['bearing_votes_m'])
            inn = (v['E'] >= x0) & (v['E'] < x1) & (v['N'] >= y0) & (v['N'] < y1); grids[y].append(np.stack([v['E'][inn], v['N'][inn], v['shadow'][inn]], 1))
            for r in v['strokes']:
                b = r['base_en']
                if x0 <= b[0] < x1 and y0 <= b[1] < y1 and not r['edge'] and r['shadow_m'] >= Q['SHADOW_MIN_M']:
                    r['year'] = y; r['tile'] = t['id']; S.append(r)
    B = np.array([r['base_en'] for r in S]); s, dist, leg = lapgeo.where(B[:, 0], B[:, 1])
    ok = (dist <= Q['POST_CORRIDOR_M']) & ~((s >= lapgeo.COVERED_S[0]) & (s <= lapgeo.COVERED_S[1]) & (dist < 20))
    S = [r for r, k in zip(S, ok) if k]; B = B[ok]; s, dist, leg = s[ok], dist[ok], leg[ok]
    gt = {}
    for y in YEARS:
        if grids[y]:
            g = np.concatenate(grids[y]); gt[y] = (cKDTree(g[:, :2]), g[:, 2])
    def shaded(y, p):
        if y not in gt:
            return None
        d, i = gt[y][0].query(p); return bool(gt[y][1][i] > 0.5) if d < 1.5 else None
    par = list(range(len(S)))
    def f(a):
        while par[a] != a:
            par[a] = par[par[a]]; a = par[a]
        return a
    tr = cKDTree(B)
    for a, b in tr.query_pairs(Q['JOIN_M']):
        par[f(a)] = f(b)
    groups = collections.defaultdict(list)
    for i in range(len(S)):
        groups[f(i)].append(i)
    crowd = np.array([len(tr.query_ball_point(b, Q['CROWD_R_M'])) for b in B])
    cands = []; dropped = collections.Counter(); L = lapgeo.lap()
    for g in groups.values():
        yrs = sorted({S[i]['year'] for i in g}, reverse=True); per = {}
        for y in yrs:
            i = max((i for i in g if S[i]['year'] == y), key=lambda i: S[i]['shadow_m']); r = S[i]
            per[y] = {'base_en': [round(float(v), 2) for v in r['base_en']], 'shadow_m': round(r['shadow_m'], 2), 'shadow_width_m': round(r['width_m'], 2), 'shadow_bearing_deg': round(r['bearing'], 1),
                      'foot_bright': round(r['foot_bright']), 'tip_mass_m2': round(r['tip_mass_m2'], 2), 'on_roadway': r['on_road'],
                      'arms': [{k: round(v, 2) for k, v in a.items()} for a in r['arms']]}
        P = np.array([per[y]['base_en'] for y in yrs]); pos = P.mean(0) if 2022 not in per or len(yrs) > 2 else np.array(per[2022]['base_en'])
        if len(yrs) >= 2:
            pos = np.median(P, 0) if len(yrs) == 3 else P.mean(0)
        spread = float(max(np.hypot(*(P[a] - P[b])) for a in range(len(P)) for b in range(len(P)))) if len(P) > 1 else None
        shade = {y: shaded(y, pos) for y in YEARS}; tree = np.mean([per[y]['tip_mass_m2'] > Q['TREE_TIP_M2'] for y in yrs]) > 0.5
        if len(yrs) == 1:
            others = [y for y in YEARS if y != yrs[0] and y in gt]
            if any(shade[y] is False for y in others):
                dropped['one year only, another year shows sunlit ground and no stroke there'] += 1; continue
            if per[yrs[0]]['on_roadway']:
                dropped['one year only, base inside the roadway'] += 1; continue
            if max(crowd[i] for i in g) - len(g) >= Q['CROWD_N']:
                dropped['one year only, in a crowd of strokes (a fence, a tree)'] += 1; continue
            verdict = 'one-year'
        else:
            verdict = 'tree?' if tree else 'post'
        k = int(np.argmin(np.hypot(L['E'] - pos[0], L['N'] - pos[1]))); lon, lat = lapgeo.lonlat(pos[0], pos[1])
        cands.append({'en': [round(float(pos[0]), 2), round(float(pos[1]), 2)], 'lonlat': [round(float(lon), 7), round(float(lat), 7)], 's_m': round(float(L['s'][k]), 1),
                      'off_lap_m': round(float(np.hypot(L['E'][k] - pos[0], L['N'][k] - pos[1])), 1), 'leg': L['legs'][int(L['leg'][k])], 'years': yrs, 'spread_m': None if spread is None else round(spread, 2),
                      'in_building_shadow': {str(y): shade[y] for y in YEARS}, 'reader_verdict': verdict, 'per_year': {str(y): per[y] for y in yrs}})
    cands.sort(key=lambda c: c['s_m'])
    for k, c in enumerate(cands):
        c['id'] = k
    meta = {'thresholds_invented': Q, 'strokes_in_corridor': len(S), 'candidates': len(cands), 'by_verdict': dict(collections.Counter(c['reader_verdict'] for c in cands)),
            'dropped': dict(dropped), 'sun_shadow_bearing_deg_per_year': {str(y): {'median': float(np.median([v[0] for v in d.values()])), 'p05_p95': [float(q) for q in np.percentile([v[0] for v in d.values()], [5, 95])],
                                                                             'tiles_on_the_prior': sum(1 for v in d.values() if v[1] == 0.0)} for y, d in sun.items()}}
    if save:
        json.dump({'meta': meta, 'candidates': cands}, open(os.path.join(cache, 'posts_candidates.json'), 'w'))
    print(meta); return (cands, meta) if not save else cands


def panels(cache, cands):
    import lapview
    from PIL import Image
    L = lapgeo.lap(); os.makedirs(os.path.join(cache, 'panels'), exist_ok=True); ps = []
    for s0 in np.arange(0, L['length'], Q['PANEL_STEP_M']):
        if lapgeo.COVERED_S[0] + 30 <= s0 <= lapgeo.COVERED_S[1] - 30:
            continue
        k = int(s0); ps.append({'id': f'P{len(ps):03d}', 's_m': float(s0), 'c': [float(L['E'][k]), float(L['N'][k])], 'leg': L['legs'][int(L['leg'][k])]})
    PC = np.array([p['c'] for p in ps]); h = Q['PANEL_M'] / 2
    for c in cands:
        d = np.max(np.abs(PC - np.array(c['en'])), 1); c['panel'] = ps[int(np.argmin(d))]['id'] if d.min() <= h - 1.0 else ps[int(np.argmin(np.hypot(*(PC - np.array(c['en'])).T)))]['id']
    for p in ps:
        box = (p['c'][0] - h, p['c'][1] - h, p['c'][0] + h, p['c'][1] + h); ims = []
        for y in (2022, 2020):
            v = lapview.View(cache, y, box, zoom=1.0)
            for c in cands:
                e = c['en']
                if not (box[0] <= e[0] <= box[2] and box[1] <= e[1] <= box[3]):
                    continue
                if c['panel'] == p['id']:
                    col = {'post': (255, 255, 0), 'tree?': (255, 150, 0), 'one-year': (0, 255, 255)}[c['reader_verdict']]
                    v.ring(e[0], e[1], 9, col, 2); v.text(e[0], e[1], str(c['id']), col, dx=10, dy=-14)
                else:
                    v.ring(e[0], e[1], 6, (150, 150, 150), 1)
            v.grid(5); v.text(box[0] + 1, box[3] - 1, f"{p['id']} {y}", (255, 255, 255), dx=40, dy=18); ims.append(v.im)
        W = sum(i.width for i in ims) + 6; out = Image.new('RGB', (W, max(i.height for i in ims)), (255, 0, 255)); x = 0
        for i in ims:
            out.paste(i, (x, 0)); x += i.width + 6
        out.save(os.path.join(cache, 'panels', p['id'] + '.jpg'), quality=88)
        p['box_en'] = [round(v_, 1) for v_ in box]; p['candidates'] = [c['id'] for c in cands if c['panel'] == p['id']]
    json.dump(ps, open(os.path.join(cache, 'panels.json'), 'w'), indent=1)
    json.dump({'candidates': cands}, open(os.path.join(cache, 'posts_candidates_panels.json'), 'w'))
    print(len(ps), 'panels;', sum(len(p['candidates']) for p in ps), 'candidates placed')


def cluster2(cache):
    """Second pass, after posts_tile.py --known: the strokes re-read with each tile-year's own sun bearing. A new candidate
    is one with no first-pass candidate within R2_OLD_M (those have their verdict) and no accepted post within R2_POST_M.
    Only the new ones, and first-pass rings a reader could not find on its panel, go back to the eye, on panels that also
    show every post accepted so far (green squares) so that what is still missing can be added."""
    import lapview
    from PIL import Image
    import posts_apply
    old = json.load(open(os.path.join(cache, 'posts_candidates_panels.json')))['candidates']; cands, meta = cluster(cache, save=False)
    V, added, _, _ = posts_apply.load_verdicts()
    acc = [np.array(lapgeo.en(*p['lonlat']), float) for f in ('lamps.json', 'signals.json') for p in json.load(open(os.path.join(HERE, f)))['posts']]
    A = np.array(acc); at = cKDTree(A); ot = cKDTree(np.array([c['en'] for c in old])); new = []
    for c in cands:
        if ot.query(c['en'])[0] <= Q['R2_OLD_M'] or at.query(c['en'])[0] <= Q['R2_POST_M']:
            continue
        c['id'] = 10000 + len(new); new.append(c)
    lost = [c for c in old if (V.get(c['id']) or {}).get('note') and 'ring not found' in str(V[c['id']]['note'])]
    show = new + lost; panels = json.load(open(os.path.join(cache, 'panels.json'))); h = Q['PANEL_M'] / 2; ps = {}
    PC = np.array([p['c'] for p in panels])
    for c in show:
        d = np.max(np.abs(PC - np.array(c['en'])), 1); k = int(np.argmin(d))
        if d[k] <= h - 2.0:
            pid = 'R' + panels[k]['id'][1:]; ctr = panels[k]['c']
        else:
            pid = 'RX%03d' % len([q for q in ps if q.startswith('RX')]); ctr = c['en']
            hit = [q for q, v in ps.items() if q.startswith('RX') and max(abs(v['c'][0] - c['en'][0]), abs(v['c'][1] - c['en'][1])) <= h - 2.0]
            if hit:
                pid = hit[0]; ctr = ps[pid]['c']
        ps.setdefault(pid, {'id': pid, 'c': ctr, 'candidates': []})['candidates'].append(c['id']); c['panel'] = pid
    os.makedirs(os.path.join(cache, 'panels_r2'), exist_ok=True)
    for pid, p in ps.items():
        box = (p['c'][0] - h, p['c'][1] - h, p['c'][0] + h, p['c'][1] + h); ims = []
        for y in (2022, 2020):
            v = lapview.View(cache, y, box, zoom=1.0)
            for a in A:
                if box[0] <= a[0] <= box[2] and box[1] <= a[1] <= box[3]:
                    v.square(a[0], a[1], 6, (0, 255, 0), 1)
            for c in show:
                e = c['en']
                if c['panel'] == pid:
                    col = {'post': (255, 255, 0), 'tree?': (255, 150, 0), 'one-year': (0, 255, 255)}[c['reader_verdict']]
                    v.ring(e[0], e[1], 9, col, 2); v.text(e[0], e[1], str(c['id']), col, dx=10, dy=-14)
            v.grid(5); v.text(box[0] + 1, box[3] - 1, f"{pid} {y}", (255, 255, 255), dx=40, dy=18); ims.append(v.im)
        out = Image.new('RGB', (sum(i.width for i in ims) + 6, max(i.height for i in ims)), (255, 0, 255)); x = 0
        for i in ims:
            out.paste(i, (x, 0)); x += i.width + 6
        out.save(os.path.join(cache, 'panels_r2', pid + '.jpg'), quality=88); p['box_en'] = [round(b, 1) for b in box]
    json.dump(list(ps.values()), open(os.path.join(cache, 'panels_r2.json'), 'w'), indent=1)
    json.dump({'meta': meta, 'candidates': new}, open(os.path.join(cache, 'posts_candidates_r2.json'), 'w'))
    print(len(new), 'new candidates;', len(lost), 'first-pass rings not found;', len(ps), 'panels')


if __name__ == '__main__':
    cmd, cache = sys.argv[1], sys.argv[2]
    if cmd == 'cluster2':
        cluster2(cache)
    if cmd == 'cluster':
        c = cluster(cache); panels(cache, c)
    elif cmd == 'apply':
        import posts_apply; posts_apply.main(cache)

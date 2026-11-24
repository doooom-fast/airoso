"""lamps.json and signals.json from the candidates and the eye's verdicts (posts_lap.py apply).

Every post in the two files was looked at on a panel (cache/panels/Pnnn.jpg: 2022 beside 2020) and given a class by eye;
the reader's own verdict stands beside it. A post the eye added is placed at the foot of the nearest shadow stroke of
any year within EYE_SNAP_M (grade measured), else where the eye read it off the panel's 5 m ticks (grade detected,
about +-1.5 m). A candidate the eye called not_a_post or cannot_tell is not in the inventory; both are counted.

grade      measured: the foot of a shadow read off the aerial. Where two or three flight years' shadows share the foot
           ('years' has two or more) the post is CONFIRMED by an independent reading and spread_m is their disagreement.
           detected: placed by eye only.
heights    not written. The shadow length per year is ('shadow_m'): a height needs the sun's elevation at each
           flight line's hour, which SURVEY.md explains was not derived cleanly.
signals    per OSM signal node and per physical junction: the masts and signal posts within SIGNAL_JUNCTION_R_M. Zero is a
           finding and is written as one, with what the pictures show there (shadow share).
"""
import collections, glob, json, math, os, pickle, sys, time
import numpy as np
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import lapgeo  # noqa: E402
import posts_lap as pl  # noqa: E402

SIGNAL = ('signal_mast', 'signal_post')
KEEP = ('lamp', 'signal_mast', 'signal_post', 'sign_or_small_post', 'utility_pole', 'post_unknown')


def load_verdicts():
    V = {}; added = []; files = sorted(glob.glob(os.path.join(HERE, 'eye', 'verdicts_*.json'))); panels_read = {}
    for f in files:
        d = json.load(open(f))
        for pid, p in d.get('panels', {}).items():
            panels_read.setdefault(pid, []).append(os.path.basename(f))
            for cid, cls in p.get('candidates', {}).items():
                V[int(cid)] = {'class': cls if isinstance(cls, str) else cls.get('class'), 'note': None if isinstance(cls, str) else cls.get('note'), 'file': os.path.basename(f), 'panel': pid}
            for a in p.get('added', []):
                added.append({**a, 'panel': pid, 'file': os.path.basename(f)})
    return V, added, panels_read, [os.path.basename(f) for f in files]


def main(cache):
    cands = json.load(open(os.path.join(cache, 'posts_candidates_panels.json')))['candidates']; meta = json.load(open(os.path.join(cache, 'posts_candidates.json')))['meta']
    r2 = os.path.join(cache, 'posts_candidates_r2.json')
    if os.path.exists(r2):
        d2 = json.load(open(r2)); cands = cands + d2['candidates']; meta = {'first_pass': meta, 'second_pass_with_the_sun_bearing_from_confirmed_posts': {**d2['meta'], 'new_candidates': len(d2['candidates'])}}
    panels = json.load(open(os.path.join(cache, 'panels.json'))); V, added, panels_read, vfiles = load_verdicts(); L = lapgeo.lap()
    # every stroke of every year, for placing what the eye added
    SB = []; SY = []; SL = []
    for t in lapgeo.tiles():
        p = os.path.join(cache, 'posts', t['id'] + '.pkl')
        if os.path.exists(p):
            d = pickle.load(open(p, 'rb')); x0, y0, x1, y1 = t['cell']
            for y, v in d['years'].items():
                for r in v['strokes']:
                    b = r['base_en']
                    if x0 <= b[0] < x1 and y0 <= b[1] < y1:
                        SB.append(b); SY.append(y); SL.append(r['shadow_m'])
    SB = np.array(SB); st = cKDTree(SB)
    posts = []; tally = collections.Counter(); unchecked = []
    for c in cands:
        v = V.get(c['id'])
        if v is None:
            unchecked.append(c['id']); continue
        tally[(c['reader_verdict'], v['class'] if v['class'] in KEEP else v['class'])] += 1
        if v['class'] not in KEEP:
            continue
        posts.append({'class': v['class'], 'lonlat': c['lonlat'], '_en': c['en'], 'grade': 'measured', 'position_from': 'the foot of its shadow (the sun-ward end of the stroke)',
                      'years': c['years'], 'confirmed_by_second_year': len(c['years']) >= 2, 'spread_m': c['spread_m'], 'reader_verdict': c['reader_verdict'],
                      'eye': {'verdict': v['class'], 'panel': v['panel'], 'note': v['note']}, 'in_building_shadow': c['in_building_shadow'],
                      'shadow_m': {y: p['shadow_m'] for y, p in c['per_year'].items()}, 'arms': {y: p['arms'] for y, p in c['per_year'].items() if p['arms']},
                      'lamp_head_bright_at_foot': {y: p['foot_bright'] for y, p in c['per_year'].items()}, 'candidate': c['id'], 's_m': c['s_m'], 'off_lap_m': c['off_lap_m'], 'leg': c['leg']})
    P0 = np.array([p['_en'] for p in posts]) if posts else np.zeros((0, 2)); n_snap = n_eye = n_dup = n_out = 0
    for a in added:
        if a.get('class') not in KEEP:
            continue
        e = np.array([float(a['E']), float(a['N'])]); s, d, leg = lapgeo.where([e[0]], [e[1]])
        if d[0] > pl.Q['POST_CORRIDOR_M'] + 3 or (lapgeo.COVERED_S[0] <= s[0] <= lapgeo.COVERED_S[1] and d[0] < 20):
            n_out += 1; continue
        near = st.query_ball_point(e, pl.Q['EYE_SNAP_M']); pos = e; frm = 'by eye off the panel\'s 5 m ticks (about +-1.5 m)'; grade = 'detected'; yrs = []; sm = {}
        if near:
            k = min(near, key=lambda i: np.hypot(*(SB[i] - e))); pos = SB[k]; grade = 'measured'; frm = 'found by eye; placed at the foot of the nearest shadow stroke within %.1f m' % pl.Q['EYE_SNAP_M']
            grp = [i for i in st.query_ball_point(pos, pl.Q['JOIN_M'])]; yrs = sorted({int(SY[i]) for i in grp}, reverse=True); sm = {str(y): round(max(SL[i] for i in grp if SY[i] == y), 2) for y in yrs}
        allp = np.array([p['_en'] for p in posts]) if posts else np.zeros((0, 2))
        if len(allp) and np.hypot(*(allp - pos).T).min() < pl.Q['EYE_DEDUPE_M']:
            n_dup += 1; continue
        n_snap += grade == 'measured'; n_eye += grade == 'detected'
        k = int(np.argmin(np.hypot(L['E'] - pos[0], L['N'] - pos[1]))); lo, la = lapgeo.lonlat(pos[0], pos[1])
        posts.append({'class': a['class'], 'lonlat': [round(float(lo), 7), round(float(la), 7)], '_en': [float(pos[0]), float(pos[1])], 'grade': grade, 'position_from': frm, 'years': yrs,
                      'confirmed_by_second_year': len(yrs) >= 2, 'spread_m': None, 'reader_verdict': 'missed by the reader', 'eye': {'verdict': a['class'], 'panel': a['panel'], 'note': a.get('note'), 'read_at_en': [float(a['E']), float(a['N'])]},
                      'shadow_m': sm, 'arms': {}, 's_m': round(float(L['s'][k]), 1), 'off_lap_m': round(float(np.hypot(L['E'][k] - pos[0], L['N'][k] - pos[1])), 1), 'leg': L['legs'][int(L['leg'][k])]})
    for p in posts:                                   # which years' strokes start at this foot, on the strokes as last read
        if 'candidate' in p:
            grp = st.query_ball_point(np.array(p['_en']), pl.Q['JOIN_M'])
            yrs = sorted({int(SY[i]) for i in grp} | set(p['years']), reverse=True)
            if len(yrs) > len(p['years']):
                p['years'] = yrs; p['confirmed_by_second_year'] = len(yrs) >= 2
                for y in yrs:
                    if str(y) not in p['shadow_m']:
                        p['shadow_m'][str(y)] = round(max(SL[i] for i in grp if SY[i] == y), 2)
                if p['spread_m'] is None and len(yrs) >= 2:
                    b_ = [np.mean([SB[i] for i in grp if SY[i] == y], 0) for y in yrs if any(SY[i] == y for i in grp)] + [np.array(p['_en'])]
                    p['spread_m'] = round(float(max(np.hypot(*(u - v)) for u in b_ for v in b_)), 2)
    cf = os.path.join(HERE, 'eye', 'corrections.json'); corr = {'removed': 0, 'moved': 0, 'flagged': 0}
    if os.path.exists(cf):
        cj = json.load(open(cf))
        def near(E, N):
            d = [math.hypot(p['_en'][0] - E, p['_en'][1] - N) for p in posts]; k = int(np.argmin(d)) if d else -1
            return k if k >= 0 and d[k] <= 0.8 else None
        for r in cj.get('remove', []):
            k = near(r['E'], r['N'])
            if k is not None:
                posts.pop(k); corr['removed'] += 1
        for r in cj.get('move', []):
            k = near(r['E'], r['N'])
            if k is not None:
                p = posts[k]; p['_en'] = [r['to_E'], r['to_N']]; lo, la = lapgeo.lonlat(r['to_E'], r['to_N'])
                p['lonlat'] = [round(float(lo), 7), round(float(la), 7)]; p['grade'] = 'detected'; p['position_from'] = 'moved by eye to the foot: ' + r['why']; corr['moved'] += 1
        for r in cj.get('flag', []):
            k = near(r['E'], r['N'])
            if k is not None:
                posts[k]['position_note'] = r['note']; corr['flagged'] += 1
    rd_corr = corr
    posts.sort(key=lambda p: p['s_m'])
    for k, p in enumerate(posts):
        p['id'] = ('g' if p['class'] in SIGNAL else 'l') + f'{k:04d}'; p['height_m'] = None
    PE = np.array([p['_en'] for p in posts]) if posts else np.zeros((0, 2))
    # the reader against the eye
    is_post = lambda cls: cls in KEEP
    rd = {'candidates': len(cands), 'checked_by_eye': len(cands) - len(unchecked), 'unchecked': unchecked,
          'eye_says_post': sum(n for (rv, cls), n in tally.items() if is_post(cls)), 'eye_says_not_a_post': sum(n for (rv, cls), n in tally.items() if cls == 'not_a_post'),
          'eye_cannot_tell': sum(n for (rv, cls), n in tally.items() if cls == 'cannot_tell'),
          'by_reader_verdict': {rv: {'post': sum(n for (r2, cls), n in tally.items() if r2 == rv and is_post(cls)), 'not_a_post': sum(n for (r2, cls), n in tally.items() if r2 == rv and cls == 'not_a_post'),
                                     'cannot_tell': sum(n for (r2, cls), n in tally.items() if r2 == rv and cls == 'cannot_tell')} for rv in ('post', 'tree?', 'one-year')},
          'corrections_by_eye_after_the_second_pass': rd_corr, 'added_by_eye': {'placed_on_a_shadow_foot': int(n_snap), 'placed_by_eye_only': int(n_eye), 'duplicates_of_a_candidate_dropped': n_dup, 'outside_the_corridor_dropped': n_out}}
    tp = rd['eye_says_post']; rd['reader_precision_against_the_eye'] = round(tp / max(tp + rd['eye_says_not_a_post'], 1), 3); rd['reader_recall_against_the_eye'] = round(tp / max(tp + n_snap + n_eye, 1), 3)
    common = {'written_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'frame': {'origin_lonlat': list(lapgeo.ORIGIN), 'corridor_half_width_m': pl.Q['POST_CORRIDOR_M']},
              'sources': {'aerials': 'DRCOG 3-inch, 2022 / 2020 / 2018 (drapparchive.s3.amazonaws.com), by HTTP range', 'reader': 'posts_tile.py + posts_lap.py', 'eye': 'panels of 2022 beside 2020; verdict files: ' + ', '.join(vfiles)},
              'reader': {**meta, 'against_the_eye': rd},
              'heights': 'not written: see SURVEY.md (the sun\'s elevation was not derived cleanly per flight line); shadow_m per year is kept so a height follows once it is',
              'unsurveyed': [{'what': 'Stout St under the Colorado Convention Center', 's_m': list(lapgeo.COVERED_S), 'why': 'covered: no aerial sees it'}]}
    def strip(p):
        return {k: v for k, v in p.items() if not k.startswith('_')}
    # stretches: every panel with what it holds, so an empty stretch is a declared none
    stretches = []
    for pn in panels:
        b = pn['box_en']; inside = [p for p in posts if b[0] <= p['_en'][0] <= b[2] and b[1] <= p['_en'][1] <= b[3]]
        stretches.append({'panel': pn['id'], 's_m': pn['s_m'], 'leg': pn['leg'], 'read_by_eye': pn['id'] in panels_read, 'lamps_and_other_posts': sum(1 for p in inside if p['class'] not in SIGNAL),
                          'signal_masts_and_posts': sum(1 for p in inside if p['class'] in SIGNAL), **({'none': True} if not inside and pn['id'] in panels_read else {})})
    lamps = [strip(p) for p in posts if p['class'] not in SIGNAL]; sigs = [strip(p) for p in posts if p['class'] in SIGNAL]
    def shares(ps):
        n = max(len(ps), 1); return {'measured': round(sum(1 for p in ps if p['grade'] == 'measured') / n, 3), 'detected': round(sum(1 for p in ps if p['grade'] == 'detected') / n, 3),
                                     'confirmed_by_a_second_flight_year': round(sum(1 for p in ps if p['confirmed_by_second_year']) / n, 3)}
    sp = [p['spread_m'] for p in posts if p.get('spread_m') is not None]
    acc = {'posts_with_two_or_more_years': len(sp), 'spread_m_p50_p84_p95': [round(float(v), 2) for v in np.percentile(sp, [50, 84, 95])] if sp else None}
    json.dump({'_doc': 'Streetlights and every other post on the lap corridor that is not a signal (PLAN 4b). Each was seen by eye on a panel; the class is the eye\'s. '
                       'What a post carries beyond what the eye could name (fixture type, sign faces) is not read. See SURVEY.md.', **common,
               'counts': {'posts': len(lamps), 'by_class': dict(collections.Counter(p['class'] for p in lamps)), 'by_leg': dict(collections.Counter(p['leg'] for p in lamps))},
               'grade_shares': shares(lamps), 'position_check': acc, 'stretches': stretches, 'posts': lamps}, open(os.path.join(HERE, 'lamps.json'), 'w'), indent=1)
    # signals per OSM node and per junction
    o = lapgeo.osm(); J = []
    for g in lapgeo.junctions():
        E = float(np.mean([r['E'] for r in g])); N = float(np.mean([r['N'] for r in g])); nodes = [r['node'] for r in g if r['signal_tag']]
        near = [p for p in posts if p['class'] in SIGNAL and math.hypot(p['_en'][0] - E, p['_en'][1] - N) <= pl.Q['SIGNAL_JUNCTION_R_M']]
        lo, la = lapgeo.lonlat(E, N); s_ = sorted(r['s'] for r in g)
        under = lapgeo.COVERED_S[0] <= s_[0] <= lapgeo.COVERED_S[1]; off = float(lapgeo.where([E], [N])[1][0])
        J.append({'junction': ' / '.join(sorted({n for r in g for n in r['lap_street']}) + sorted({n for r in g for n in r['cross'] if n not in r['lap_street']})), 's_m': [round(v, 1) for v in s_],
                  'centre_lonlat': [round(float(lo), 7), round(float(la), 7)], 'osm_signal_nodes': nodes, 'osm_tags_a_signal': bool(nodes),
                  'signal_masts_found': sum(1 for p in near if p['class'] == 'signal_mast'), 'signal_posts_found': sum(1 for p in near if p['class'] == 'signal_post'), 'ids': [p['id'] for p in near],
                  'off_lap_m': round(off, 1), **({'finding': ('outside the surveyed corridor: the OSM way carrying this node runs %.0f m past the lap; not surveyed, nothing claimed' % off) if off > lapgeo.CORRIDOR_M else ('no mast or signal post found within %d m' % pl.Q['SIGNAL_JUNCTION_R_M'] + (' (under or beside the Convention Center roof: unsurveyed)' if under else ''))} if nodes and not near else {}),
                  **({'finding': 'masts found where OSM tags no signal'} if near and not nodes else {})})
    J.sort(key=lambda j: j['s_m'][0])
    per_node = []
    for j in J:
        for n in j['osm_signal_nodes']:
            per_node.append({'osm_node': n, 'junction': j['junction'], 'signal_masts_found_at_its_junction': j['signal_masts_found'], 'signal_posts_found_at_its_junction': j['signal_posts_found']})
    orphan = [p['id'] for p in posts if p['class'] in SIGNAL and not any(p['id'] in j['ids'] for j in J)]
    json.dump({'_doc': 'Signal masts and signal posts on the lap corridor, and the count at every junction OSM tags as signalled (PLAN 4b). signal_mast: a pole with an arm over the roadway '
                       '(signal heads hang from it); signal_post: a short post or pedestal by the kerb carrying signal or pedestrian heads. Classes are the eye\'s, off the aerial. Heads, their '
                       'number and their faces are not read. See SURVEY.md.', **common,
               'counts': {'signal_masts': sum(1 for p in sigs if p['class'] == 'signal_mast'), 'signal_posts': sum(1 for p in sigs if p['class'] == 'signal_post'),
                          'osm_signal_nodes_on_the_lap': len(per_node), 'junctions_osm_tags_signalled': sum(1 for j in J if j['osm_tags_a_signal']),
                          'signalled_junctions_on_the_lap': sum(1 for j in J if j['osm_tags_a_signal'] and j['off_lap_m'] <= lapgeo.CORRIDOR_M), 'signalled_junctions_off_the_lap_not_surveyed': sum(1 for j in J if j['osm_tags_a_signal'] and j['off_lap_m'] > lapgeo.CORRIDOR_M), 'signalled_junctions_on_the_lap_with_no_mast_or_post_found': sum(1 for j in J if j['osm_tags_a_signal'] and not j['ids'] and j['off_lap_m'] <= lapgeo.CORRIDOR_M),
                          'masts_per_signalled_junction_on_the_lap': dict(collections.Counter(j['signal_masts_found'] for j in J if j['osm_tags_a_signal'] and j['off_lap_m'] <= lapgeo.CORRIDOR_M)), 'signal_posts_not_at_a_tagged_junction': orphan},
               'grade_shares': shares(sigs), 'position_check': acc, 'junctions': J, 'osm_signal_nodes': per_node, 'posts': sigs}, open(os.path.join(HERE, 'signals.json'), 'w'), indent=1)
    print('lamps', len(lamps), 'signals', len(sigs), rd, acc)


if __name__ == '__main__':
    main(sys.argv[1])

"""Denver Grand Prix 0.1.1: where every surveyed post goes, against the edge of record, and which PR 60 model fits.

    PY=/Volumes/Sundowning/Claude/airoso-data/venv/bin/python
    $PY tracks/denver-grand-prix/source/furniture/plan_placements.py \
        [--survey <dir holding lamps.json + signals.json>]  [--models <dir holding signals.json + streetlight_posts.json>]

Defaults: the survey at tracks/denver-grand-prix/source/survey/ (PR 66) and the models at assets/models/ (PR 60), i.e.
the integration branch once both are merged. Writes placements.plan.json beside this file. Data only: nothing placed.

INPUTS
  posts      PR 66's lamps.json (lamps, sign / small posts, utility poles, unknown posts) and signals.json (signal masts
             and signal posts), each with its position (foot of its shadow, graded), the eye's class and note, and its
             shadow length per flight year.
  edges      source/widths/widths.json: both edges of record every 2.5 m along OSM's lap line (ENU about Colfax /
             Sherman, + = driver's left).
  models     PR 60's catalogues: mast arms 25 / 35 / 45 ft, pedestal, pushbutton post, signal heads; lamp classes
             ped_acorn, ped_globe, arterial_single, arterial_twin; plus the owned led_cobra.

PER POST
  station    s on the lap line (nearest point, 2.5 m stations interpolated), side (left / right of the driver), the
             perpendicular offset from the line, and OFFSET FROM THE EDGE OF RECORD on that side: + = beyond the kerb
             (on the walk), - = inside it (in the roadway, or on a median / island the record runs past).
  fronts     'lap' when the post stands within FRONT_MAX_M behind the lap's kerb; 'cross_street' when another OSM
             carriageway's line is nearer than the lap's kerb (a corner post that serves the side road); 'off_corridor'
             otherwise. A post with offset < -INSIDE_TOL_M is flagged 'inside_edge' (a median, an island, or a reading
             to check).
  class / model, by the eye first and the shadow second:
    signal_mast  -> signal_mast_arm_25 / _35 / _45. Arm direction from the eye's note ("arm reaches south"). When the
                 arm points across the lap (within 45 degrees of the lap's normal toward the road), the arm length
                 needed is the post's offset behind the kerb + the far side of the lanes it serves (to the middle of the
                 carriageway); the shortest model that reaches is chosen. An arm across a cross street, or no direction
                 in the note: 35 ft [typical], marked.
    signal_post  -> signal_pedestal when its shadow is short (a pedestal is 3.05 m), else a tall signal pole, which PR
                 60 does not make: GAP, with the pedestal named as the stand-in. carries_lamp adds a lamp row.
    lamp         -> pedestrian (ped_globe / ped_acorn) or arterial (arterial_single / arterial_twin / led_cobra):
                 the eye's words first ("globe", "acorn", "pedestrian", "cobra", "arm", "twin", "two arms"),
                 then the height from the shadow (shadow over the year's median signal-mast shadow, times the mast's
                 pole height [typical]): under PED_MAX_M pedestrian, else arterial.
    sign_or_small_post -> a sign post; face not read (PR 66 has no faces): the junction's OSM rule decides it later.
    utility_pole, post_unknown -> listed, not placed (GAP / unknown).

Every threshold is [invented] and written into the output.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys

import numpy as np
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, *[os.pardir] * 4))
T = os.path.join(ROOT, 'tracks', 'denver-grand-prix')
sys.path.insert(0, ROOT)
from scripts.aerial.engine import geom  # noqa: E402
from scripts.aerial.engine.ortho import mpd  # noqa: E402

ORIGIN = (-104.9849, 39.7401)
MLON, MLAT = mpd(ORIGIN[1])

Q = dict(FRONT_MAX_M=8.0, INSIDE_TOL_M=0.5, PED_MAX_M=5.5, MAST_POLE_M=7.6, PEDESTAL_SHADOW_MAX_RATIO=0.55,
         ARM_ACROSS_DEG=45.0, ARM_DEFAULT='signal_mast_arm_35', ARM_REACH_FRAC=0.75)

DIRS = {'north': 0, 'n': 0, 'north-east': 45, 'northeast': 45, 'ne': 45, 'east': 90, 'e': 90, 'south-east': 135,
        'southeast': 135, 'se': 135, 'south': 180, 's': 180, 'south-west': 225, 'southwest': 225, 'sw': 225,
        'west': 270, 'w': 270, 'north-west': 315, 'northwest': 315, 'nw': 315}


def en(lon, lat):
    return (np.asarray(lon, float) - ORIGIN[0]) * MLON, (np.asarray(lat, float) - ORIGIN[1]) * MLAT


PTS16 = {'n': 0, 'nne': 22.5, 'ne': 45, 'ene': 67.5, 'e': 90, 'ese': 112.5, 'se': 135, 'sse': 157.5, 's': 180,
         'ssw': 202.5, 'sw': 225, 'wsw': 247.5, 'w': 270, 'wnw': 292.5, 'nw': 315, 'nnw': 337.5}
WORD = r'(north-east|north-west|south-east|south-west|northeast|northwest|southeast|southwest|north|south|east|west|' \
       r'nne|ene|ese|sse|ssw|wsw|wnw|nnw|ne|nw|se|sw|n|s|e|w)'


def _b(w):
    w = w.lower()
    return DIRS[w] if w in DIRS else PTS16.get(w)


def arm_bearing(note):
    """The bearing of the first signal arm the eye names: 'arm reaches / reaching <dir>', '<dir> arm', 'arms <dir>',
    16-point abbreviations included; a luminaire arm ('luminaire arm west') is skipped. None if none."""
    if not note:
        return None
    t = note.lower()
    for m in re.finditer(r'(luminaire\s+)?arms?\s+(?:with\s+heads\s+)?(?:reach(?:es|ing)?\s+)?(?:\w+\s+)?' + WORD + r'\b', t):
        if m.group(1):
            continue
        b = _b(m.group(2))
        if b is not None:
            return b
    m = re.search(r'\b' + WORD + r'\s+arm', t)
    if m and 'luminaire' not in t[max(0, m.start() - 12):m.start()]:
        return _b(m.group(1))
    return None


def lamp_kind(note, height):
    t = (note or '').lower()
    if 'cobra' in t:
        return 'arterial', 'led_cobra', 'eye: cobra'
    if 'twin' in t or 'two arms' in t or 'double' in t:
        return 'arterial', 'arterial_twin', 'eye: two arms'
    if 'acorn' in t:
        return 'pedestrian', 'ped_acorn', 'eye: acorn'
    if 'globe' in t or 'pedestrian' in t or 'round' in t:
        return 'pedestrian', 'ped_globe', 'eye: globe / pedestrian'
    if 'arm' in t or 'luminaire' in t or 'tall' in t:
        if height is not None and height < Q['PED_MAX_M'] and 'tall' not in t:
            return 'pedestrian', 'ped_globe', 'shadow height (note names an arm but the post is short)'
        return 'arterial', 'arterial_single', 'eye: arm / luminaire / tall'
    if height is None:
        return 'unknown', None, 'no note word and no shadow'
    if height < Q['PED_MAX_M']:
        return 'pedestrian', 'ped_globe', 'shadow height [typical model]'
    return 'arterial', 'arterial_single', 'shadow height [typical model]'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--survey', default=os.path.join(T, 'source', 'survey'))
    ap.add_argument('--models', default=os.path.join(ROOT, 'assets', 'models'))
    a = ap.parse_args()
    lamps = json.load(open(os.path.join(a.survey, 'lamps.json')))
    sigs = json.load(open(os.path.join(a.survey, 'signals.json')))
    msig = json.load(open(os.path.join(a.models, 'signals.json')))
    mlamp = json.load(open(os.path.join(a.models, 'streetlight_posts.json')))
    W = json.load(open(os.path.join(T, 'source', 'widths', 'widths.json')))
    st = W['stations']
    S = np.array([x['s'] for x in st])
    P = np.array([x['line_EN'] for x in st])
    LEN = W['meta']['lap_length_m']
    Tn, Ln = geom.normals(P, closed=True)
    EL = np.array([x['left']['offset'] for x in st])
    ER = np.array([x['right']['offset'] for x in st])
    # a fine line (0.5 m) for the nearest-point projection
    s_f = np.arange(0, LEN, 0.5)
    Pf = np.stack([np.interp(s_f, np.r_[S, LEN], np.r_[P[:, 0], P[0, 0]]),
                   np.interp(s_f, np.r_[S, LEN], np.r_[P[:, 1], P[0, 1]])], 1)
    Tf, Lf = geom.normals(Pf, closed=True)
    tree = cKDTree(Pf)
    # other OSM carriageways (the cross streets), as in widths.opposing_lines
    sys.path.insert(0, os.path.join(T, 'source', 'widths'))
    import widths as WM  # noqa: E402
    LPw = {'way': [x['way'] for x in st]}
    OT, OI, OW = WM.opposing_lines(LPw, None)

    # shadow -> height per flight year, from the signal masts (pole MAST_POLE_M [typical])
    mast_sh = {}
    for y in ('2022', '2020', '2018'):
        v = [p['shadow_m'].get(y) for p in sigs['posts'] if p['class'] == 'signal_mast' and p['shadow_m'].get(y)]
        if len(v) >= 10:
            mast_sh[y] = float(np.median(v))

    def height_of(p):
        hs = [p['shadow_m'][y] / mast_sh[y] * Q['MAST_POLE_M'] for y in p.get('shadow_m', {}) if y in mast_sh and p['shadow_m'][y]]
        return round(float(np.median(hs)), 2) if hs else None

    arms = sorted(((v['arm_length_m'], k) for k, v in msig['mast_arms'].items()))

    def place(p):
        E, N = en(*p['lonlat'])
        d, i = tree.query([E, N])
        s = float(s_f[i])
        rel = np.array([E, N]) - Pf[i]
        off = float(rel @ Lf[i])
        side = 'left' if off >= 0 else 'right'
        edge = float(np.interp(s, np.r_[S, LEN], np.r_[(EL if side == 'left' else ER), (EL if side == 'left' else ER)[0]]))
        from_edge = abs(off) - edge
        # the nearest other carriageway's line
        dd, ii = OT.query([E, N])
        cross = None
        if np.isfinite(dd):
            cross = {'way': int(OI[ii]), 'name': OW[int(OI[ii])]['tags'].get('name'), 'distance_m': round(float(dd), 2)}
        k0 = int(np.argmin(np.abs(S - s)))
        lapname = OW.get(st[k0]['way'], {}).get('tags', {}).get('name') if isinstance(st[k0]['way'], int) else None
        same = cross is not None and lapname is not None and cross['name'] is not None and \
            cross['name'].replace('West ', '').replace('East ', '').replace('North ', '') == \
            lapname.replace('West ', '').replace('East ', '').replace('North ', '')
        if -Q['INSIDE_TOL_M'] <= from_edge <= Q['FRONT_MAX_M'] and not (cross and cross['distance_m'] < from_edge):
            fronts = 'lap'
        elif cross and cross['distance_m'] <= Q['FRONT_MAX_M'] + 6:
            fronts = 'opposing_carriageway' if same else 'cross_street'
        elif from_edge < -Q['INSIDE_TOL_M']:
            fronts = 'lap'
        else:
            fronts = 'off_corridor'
        k = int(np.argmin(np.abs(S - s)))
        out = {'id': p['id'], 'survey_class': p['class'], 'grade': p['grade'], 'lonlat': p['lonlat'],
               'EN': [round(float(E), 2), round(float(N), 2)], 's': round(s, 1), 'side': side,
               'offset_from_line_m': round(off, 2), 'edge_of_record_m': round(edge, 2),
               'offset_from_edge_m': round(from_edge, 2), 'edge_grade': st[k][side]['grade'],
               'fronts': fronts, 'nearest_cross_carriageway': cross,
               'flags': (['inside_edge'] if from_edge < -Q['INSIDE_TOL_M'] else []) + (['covered_span'] if st[k]['covered'] else []),
               'eye_note': (p.get('eye') or {}).get('note'), 'height_from_shadow_m': height_of(p),
               'leg': st[k]['leg']}
        return out, Lf[i], Tf[i], edge, side

    rows = []
    for p in sigs['posts']:
        r, Lv, Tv, edge, side = place(p)
        if p['class'] == 'signal_mast':
            b = arm_bearing(r['eye_note'])
            r['arm_bearing_deg'] = b
            if b is None:
                r['class'] = 'signal_mast'
                r['model'] = Q['ARM_DEFAULT']
                r['model_basis'] = 'no arm direction in the eye note: 35 ft [typical]'
            else:
                v = np.array([math.sin(math.radians(b)), math.cos(math.radians(b))])
                inward = -Lv if side == 'left' else Lv                       # toward the lap's road
                ang = math.degrees(math.acos(max(-1, min(1, float(v @ inward)))))
                r['arm_vs_lap_inward_deg'] = round(ang, 1)
                if ang <= Q['ARM_ACROSS_DEG'] and r['fronts'] == 'lap':
                    other = float(np.interp(r['s'], np.r_[S, LEN], np.r_[(ER if side == 'left' else EL), (ER if side == 'left' else EL)[0]]))
                    width = edge + other
                    need = max(r['offset_from_edge_m'], 0) + Q['ARM_REACH_FRAC'] * width
                    pick = next((k for L_, k in arms if L_ >= need), arms[-1][1])
                    r['arm_needed_m'] = round(need, 2)
                    r['model'] = pick
                    r['model_basis'] = (f'arm over the lap: reach {need:.1f} m (behind kerb {max(r["offset_from_edge_m"], 0):.1f} + '
                                        f'{Q["ARM_REACH_FRAC"]} x width {width:.1f}); shortest model that reaches'
                                        + ('' if need <= arms[-1][0] else ' - LONGER THAN 45 FT: the longest model, short'))
                else:
                    r['model'] = Q['ARM_DEFAULT']
                    r['model_basis'] = 'arm over a cross street (or not across the lap): 35 ft [typical]'
            r['class'] = 'signal_mast'
            r['heads'] = 'not read (PR 66): signal_head_3 per approach lane [typical], lit steady at night (E2)'
        else:
            h = r['height_from_shadow_m']
            ped = h is not None and h <= Q['PEDESTAL_SHADOW_MAX_RATIO'] * Q['MAST_POLE_M']
            note = (r['eye_note'] or '').lower()
            if 'pedestal' in note or 'pedestrian signal post' in note or ped:
                r['class'] = 'signal_pedestal'
                r['model'] = 'signal_pedestal'
                r['model_basis'] = 'short post (shadow height) or the eye named a pedestal / pedestrian post'
            else:
                r['class'] = 'signal_pole_tall'
                r['model'] = None
                r['model_basis'] = 'GAP: PR 60 has no tall signal pole without an arm; signal_pedestal as a stand-in only'
                r['stand_in'] = 'signal_pedestal'
            if p.get('carries_lamp'):
                r['also_lamp'] = 'arterial_single'
        rows.append(r)
    for p in lamps['posts']:
        r, Lv, Tv, edge, side = place(p)
        c = p['class']
        if c == 'lamp':
            fam, model, basis = lamp_kind(r['eye_note'], r['height_from_shadow_m'])
            r['class'] = f'lamp_{fam}'
            r['model'] = model
            r['model_basis'] = basis + ('' if model != 'led_cobra' else ' (owned: tools/make_streetlight_led.py)')
        elif c == 'sign_or_small_post':
            r['class'] = 'sign_post'
            r['model'] = 'sign post + sign_plate_* (PR 60); face not read'
            r['model_basis'] = 'face from the junction\'s OSM rule (signs.json, tagged grade) or left blank'
        elif c == 'utility_pole':
            r['class'] = 'utility_pole'
            r['model'] = None
            r['model_basis'] = 'GAP: no utility pole model'
        else:
            r['class'] = 'post_unknown'
            r['model'] = None
            r['model_basis'] = 'not placed: the eye could not name it'
        rows.append(r)
    rows.sort(key=lambda r: (r['s'], r['side']))

    from collections import Counter
    cnt = Counter(r['class'] for r in rows)
    mod = Counter(str(r['model']) for r in rows)
    fr = Counter(r['fronts'] for r in rows)
    sides = Counter(r['side'] for r in rows)
    fe = np.array([r['offset_from_edge_m'] for r in rows if r['fronts'] == 'lap'])
    meta = {'script': 'tracks/denver-grand-prix/source/furniture/plan_placements.py', 'for': 'Denver 0.1.1 furniture step',
            'inputs': {'survey': 'PR 66 lamps.json + signals.json', 'models': 'PR 60 assets/models/signals.json + streetlight_posts.json',
                       'edges': 'source/widths/widths.json (edge of record)'},
            'frame': {'origin_lonlat': ORIGIN, 'offset_sign': '+ = driver left; offset_from_edge + = beyond the kerb'},
            'tuning_invented': Q, 'mast_shadow_m_median_per_year': mast_sh,
            'counts': {'posts': len(rows), 'by_class': dict(cnt), 'by_model': dict(mod), 'by_fronts': dict(fr), 'by_side': dict(sides)},
            'offset_from_edge_m_lap_fronting_p10_p50_p90': [round(float(v), 2) for v in np.percentile(fe, [10, 50, 90])] if len(fe) else None,
            'not_decided_here': ['signal heads per approach (not read)', 'sign faces (not read; OSM rule at tagged grade)',
                                 'facing / yaw: the placer turns each support to its arm bearing or to the road',
                                 'heights: from the model, not the survey (no clean sun elevation)'],
            'gaps': ['tall signal pole without an arm', 'utility pole', 'post_unknown (not placed)']}
    json.dump({'meta': meta, 'placements': rows}, open(os.path.join(HERE, 'placements.plan.json'), 'w'), indent=1)
    print(json.dumps(meta['counts'], indent=1))
    print('offset from edge (lap-fronting) p10/p50/p90', meta['offset_from_edge_m_lap_fronting_p10_p50_p90'])


if __name__ == '__main__':
    main()

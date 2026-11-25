"""The lap's geometry for the survey: one frame, the corridor, the work tiles, the junctions.

Frame: ENU metres about the Colfax / Sherman crosswalk (-104.9849, 39.7401) by the aerial engine's metres-per-degree
series (scripts.aerial.engine.ortho.mpd), the frame Ortho.load(..., origin=ORIGIN) measures in. (PLAN.md's printed x / y
use a rounder series; they differ from this frame by under 0.2 % of the distance from the origin.)

  lap()        the lap line from data/lap_line.plan.json, resampled every metre: E, N, s, leg index
  where(E, N)  nearest lap point of each query: s, distance, leg index
  tiles()      the work tiles: a 150 m grid, each tile fetched with a 12 m margin, kept when the corridor touches its cell
  junctions()  every OSM node of the lap where another street (not service / footway) meets it, with the cross street's
               tags, whether OSM tags a signal there, and nearby lap nodes merged into one junction (dual carriageways)

CORRIDOR_M is the half-width of the surveyed band about the lap's OSM line. [invented]: the brief is "the pavement plus
about 15 m each side"; the lap's carriageways are up to 17 m wide and OSM's line is not always on the centre, so 30 m.
"""
import json, math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, *[os.pardir] * 4))
T = os.path.join(ROOT, 'tracks', 'denver-grand-prix')
sys.path.insert(0, ROOT)
from scripts.aerial.engine.ortho import mpd  # noqa: E402

ORIGIN = (-104.9849, 39.7401)
MLON, MLAT = mpd(ORIGIN[1])
CORRIDOR_M = 30.0
CELL_M = 150.0
MARGIN_M = 12.0
COVERED_S = (1386.0, 1730.0)      # Stout under the Convention Center (DOSSIER section 2): unreadable from the air
NON_STREET = (None, 'service', 'footway', 'cycleway', 'path', 'steps', 'pedestrian', 'construction', 'proposed')


def en(lon, lat):
    return (np.asarray(lon, float) - ORIGIN[0]) * MLON, (np.asarray(lat, float) - ORIGIN[1]) * MLAT


def lonlat(E, N):
    return np.asarray(E, float) / MLON + ORIGIN[0], np.asarray(N, float) / MLAT + ORIGIN[1]


_LAP = None


def lap():
    global _LAP
    if _LAP is None:
        nodes = json.load(open(os.path.join(T, 'data', 'lap_line.plan.json')))['nodes']
        legs = []
        for n in nodes:
            if n['leg'] not in legs:
                legs.append(n['leg'])
        E, N = en([n['lon'] for n in nodes], [n['lat'] for n in nodes]); li = np.array([legs.index(n['leg']) for n in nodes])
        E = np.append(E, E[0]); N = np.append(N, N[0]); li = np.append(li, li[-1])            # close the lap
        d = np.hypot(np.diff(E), np.diff(N)); sv = np.concatenate([[0], np.cumsum(d)])
        s = np.arange(0, sv[-1], 1.0)
        k = np.clip(np.searchsorted(sv, s, side='right'), 1, len(sv) - 1)                      # the vertex that ENDS the segment: its leg
        _LAP = {'E': np.interp(s, sv, E), 'N': np.interp(s, sv, N), 's': s, 'leg': li[k], 'legs': legs, 'length': float(sv[-1]),
                'node_ids': [n['node'] for n in nodes], 'node_s': sv[:-1], 'node_way': [n['way'] for n in nodes]}
        from scipy.spatial import cKDTree
        _LAP['tree'] = cKDTree(np.stack([_LAP['E'], _LAP['N']], 1))
    return _LAP


def where(E, N):
    L = lap(); d, i = L['tree'].query(np.stack([np.atleast_1d(E), np.atleast_1d(N)], 1))
    return L['s'][i], d, L['leg'][i]


def tiles():
    L = lap(); out = []
    x0, x1 = L['E'].min() - CORRIDOR_M, L['E'].max() + CORRIDOR_M; y0, y1 = L['N'].min() - CORRIDOR_M, L['N'].max() + CORRIDOR_M
    i0, i1 = math.floor(x0 / CELL_M), math.floor(x1 / CELL_M); j0, j1 = math.floor(y0 / CELL_M), math.floor(y1 / CELL_M)
    for j in range(j0, j1 + 1):
        for i in range(i0, i1 + 1):
            cx0, cy0 = i * CELL_M, j * CELL_M
            dx = np.maximum(np.maximum(cx0 - L['E'], L['E'] - (cx0 + CELL_M)), 0); dy = np.maximum(np.maximum(cy0 - L['N'], L['N'] - (cy0 + CELL_M)), 0)
            if (np.hypot(dx, dy) <= CORRIDOR_M).any():
                out.append({'id': f'x{i:+04d}y{j:+04d}', 'cell': [cx0, cy0, cx0 + CELL_M, cy0 + CELL_M],
                            'box': [cx0 - MARGIN_M, cy0 - MARGIN_M, cx0 + CELL_M + MARGIN_M, cy0 + CELL_M + MARGIN_M]})
    return out


def osm():
    return json.load(open(os.path.join(T, 'source', 'osm.json')))


def junctions(merge_m=28.0):
    """Lap nodes shared with another street, merged when within merge_m of each other along one cross street pair."""
    o = osm(); L = lap(); lapways = set(L['node_way'])
    legw = json.load(open(os.path.join(T, 'data', 'lap_ways.plan.json')))['legs']; lapways |= {w for g in legw for w in g['ways']}
    byn = {}
    for w in o['ways']:
        if w['tags'].get('highway') in NON_STREET:
            continue
        for n in w['nodes']:
            byn.setdefault(n, []).append(w)
    raw = []; W = {w['id']: w for w in o['ways']}; cand = []; seen_n = set()
    for wid in lapways:                                   # every node of the lap's ways (PLAN 4b counts its 55 signals on these)
        for n in W[wid]['nodes']:
            if n not in seen_n:
                seen_n.add(n); lon, lat = o['nodes'][str(n)]; E, N = en(lon, lat); sn, dn, _ = where([E], [N])
                if dn[0] <= 1.0 or o['node_tags'].get(str(n), {}).get('highway') == 'traffic_signals':
                    cand.append((n, float(sn[0])))
    for n, sn in cand:
        ws = byn.get(n, []); other = [w for w in ws if w['id'] not in lapways]
        tg = o['node_tags'].get(str(n), {})
        if not other and tg.get('highway') != 'traffic_signals':
            continue
        lon, lat = o['nodes'][str(n)]; E, N = en(lon, lat)
        lapname = sorted({w['tags'].get('name', '?') for w in ws if w['id'] in lapways})
        raw.append({'node': n, 's': float(sn), 'E': float(E), 'N': float(N), 'lon': lon, 'lat': lat, 'signal_tag': tg.get('highway') == 'traffic_signals',
                    'node_tags': tg, 'lap_street': lapname, 'cross': sorted({w['tags'].get('name', '?') for w in other}), 'cross_ways': [w['id'] for w in other]})
    # merge the nodes of one physical junction (the two carriageways of a divided cross street, both lap passes)
    raw.sort(key=lambda r: r['s']); groups = []
    for r in raw:
        for g in groups:
            if any(math.hypot(r['E'] - q['E'], r['N'] - q['N']) <= merge_m for q in g):
                g.append(r); break
        else:
            groups.append([r])
    return groups


if __name__ == '__main__':
    L = lap(); print('lap', round(L['length'], 1), 'm;', len(L['legs']), 'legs;', len(tiles()), 'tiles')
    g = junctions(); print(len(g), 'junctions;', sum(1 for q in g if any(r['signal_tag'] for r in q)), 'with a signal tag;',
                           sum(1 for q in g for r in q if r['signal_tag']), 'signal nodes on the lap')

"""Coloured surfaces on the roadway (red: bus-lane panels, red-paved crossings; green: bike lanes and boxes) as outlines.

The tile stage (paint_tile.py) keeps a red / green patch only where two flight years show it at one place (a vehicle is
in one). Here: a patch must be bordered by roadway on at least RING_MIN of its rim (a kerbside strip of brick, a roof or
a plaza is not), pieces cut by the work tiles' edges are unioned, and each outline is simplified to SIMPLIFY_M.
What the surface is (paint, thermoplastic, coloured concrete, brick) is NOT read: the colour and the mean RGB are.
"""
import math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import lapgeo, lapview  # noqa: E402

Q = {'RING_MIN': 0.45, 'SIMPLIFY_M': 0.12, 'MIN_M2': 2.0}


def items(surfaces, cache):
    import cv2
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    polys = {'red': [], 'green': []}; dropped = 0
    for s in surfaces:
        if not s.get('bbox_ftus'):
            import json
            s['bbox_ftus'] = json.load(open(os.path.join(cache, 'img', '2022', s['tile'] + '.json')))['bbox_ftus']
        if s.get('ring_road', 1.0) < Q['RING_MIN']:
            dropped += 1; continue
        pm = np.unpackbits(s['patch'], axis=1)[:, :s['patch_shape'][1]].astype(np.uint8)
        cs, _ = cv2.findContours(pm, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE); bb = s['bbox_ftus']
        for c in cs:
            if len(c) < 3:
                continue
            x = c[:, 0, 0] + s['px0'][0] + 0.5; y = c[:, 0, 1] + s['px0'][1] + 0.5
            E, N = lapview.sp_to_en(bb[0] + x * 0.25, bb[3] - y * 0.25); p = Polygon(np.stack([E, N], 1)).buffer(0.06)
            if p.is_valid and p.area > 0.2:
                polys[s['colour']].append((p, s))
    out = []
    for col, ps in polys.items():
        if not ps:
            continue
        u = unary_union([p for p, _ in ps]); geoms = list(u.geoms) if hasattr(u, 'geoms') else [u]
        for g in geoms:
            if g.area < Q['MIN_M2']:
                continue
            src = [s for p, s in ps if p.intersects(g)]; yrs = sorted({y for s in src for y in s['years']}, reverse=True)
            ring = np.array(g.simplify(Q['SIMPLIFY_M']).exterior.coords); lo, la = lapgeo.lonlat(ring[:, 0], ring[:, 1]); c = np.array(g.centroid.coords[0])
            mr = g.minimum_rotated_rectangle.exterior.coords; e = [math.dist(mr[i], mr[i + 1]) for i in range(2)]
            see = {y: ('seen' if y in yrs else 'not seen as this colour') for y in (2022, 2020, 2018)}
            out.append({'class': 'surface', 'colour': col, 'what': 'a red / green surface on the roadway; whether paint, coloured concrete or brick is not read',
                        'area_m2': round(float(g.area), 1), 'length_m': round(max(e), 1), 'width_m': round(min(e), 1), 'mean_rgb': [round(float(np.mean([s['rgb'][k] for s in src]))) for k in range(3)],
                        'outline_lonlat': [[round(float(a), 7), round(float(b), 7)] for a, b in zip(lo, la)], 'centre_lonlat': [round(float(v), 7) for v in lapgeo.lonlat(c[0], c[1])],
                        'seen': see, 'years_seen': yrs, 'geometry_year': 'union of ' + ', '.join(map(str, yrs)), 'lidar': 'unreadable', 'lidar_returns_on_it': 0, '_firm': True, '_c': c})
    return out

"""Where the paint sits against the 2020 lidar, per work tile: the independent position check of paint.json.

    python3 paint_register.py <cache-dir>        # writes refutation/paint_registration.json

The measured paint items (crosswalk bars, lines, stop bars) are drawn as a mask on a STEP_M grid in the survey's frame;
the lidar's ground returns (class 2) in the same tile are moved over it in STEP_M steps up to MAX_M each way, and at
each shift the mean log-intensity of the returns that land on paint is taken. Paint returns more of the laser than asphalt,
so the shift where that mean peaks is where the lidar puts the paint. The lidar is another sensor flown two years earlier
(2020-05-27) and registered on its own, so the peak shift is the aerial's position error against it (plus paint moved
between the two dates, which is rare and local). A tile is reported only with at least MIN_RETURNS on paint at the peak
and a peak at least MIN_CONTRAST over the zero-shift mean of the whole search window's median.
"""
import json, math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import lapgeo  # noqa: E402

Q = {'STEP_M': 0.15, 'MAX_M': 1.2, 'MIN_RETURNS': 200, 'MIN_CONTRAST': 0.3, 'LINE_HALF_W_M': 0.08, 'BAR_HALF_W_M': 0.25}


def segs(it):
    out = []
    if it['class'] == 'crosswalk':
        out += [(b['ends_lonlat'], Q['BAR_HALF_W_M']) for b in it['bars'] if not b.get('inferred')]
    elif it['class'] == 'line' and 'dashes_lonlat' in it:
        out += [(d, Q['LINE_HALF_W_M']) for d in it['dashes_lonlat']]
    elif it['class'] == 'line':
        out.append((it['line_lonlat'], Q['LINE_HALF_W_M'] * (2.5 if it.get('pattern') == 'double solid' else 1)))
    elif it['class'] == 'stop_bar':
        out.append((it['line_lonlat'], Q['BAR_HALF_W_M']))
    return out


def main(cache):
    items = [it for it in json.load(open(os.path.join(HERE, 'paint.json')))['items'] if it['grade'] == 'measured' and it.get('seen', {}).get('2022', '').startswith('seen')]
    rows = []; st = Q['STEP_M']; k = int(round(Q['MAX_M'] / st))
    for t in lapgeo.tiles():
        lp = os.path.join(cache, 'lidar', t['id'] + '.npz')
        if not os.path.exists(lp):
            continue
        x0, y0, x1, y1 = t['box']; W = int((x1 - x0) / st) + 1; H = int((y1 - y0) / st) + 1; m = np.zeros((H, W), bool); n_it = 0
        for it in items:
            for pts, hw in segs(it):
                p = np.array([lapgeo.en(*q) for q in pts], float)
                if not ((p[:, 0] > x0).any() and (p[:, 0] < x1).any() and (p[:, 1] > y0).any() and (p[:, 1] < y1).any()):
                    continue
                n_it += 1
                for a, b in zip(p, p[1:]):
                    L = max(math.hypot(*(b - a)), 1e-6); n = int(L / (st / 2)) + 1
                    for f in np.linspace(0, 1, n):
                        c = a + (b - a) * f; d = np.array([-(b - a)[1], (b - a)[0]]) / L
                        for o in np.arange(-hw, hw + 1e-6, st / 2):
                            q = c + d * o; i, j = int((y1 - q[1]) / st), int((q[0] - x0) / st)
                            if 0 <= i < H and 0 <= j < W:
                                m[i, j] = True
        if m.sum() < 500:
            continue
        Z = np.load(lp); g = Z['cls'] == 2; E, N = lapgeo.en(Z['lon'][g], Z['lat'][g]); li = np.log1p(Z['intensity'][g].astype(float))
        best = None; grid = np.full((2 * k + 1, 2 * k + 1), np.nan); cnt = np.zeros_like(grid)
        for a in range(-k, k + 1):
            for b in range(-k, k + 1):
                j = ((E + a * st - x0) / st).astype(int); i = ((y1 - (N + b * st)) / st).astype(int); ok = (i >= 0) & (i < H) & (j >= 0) & (j < W)
                on = np.zeros(len(E), bool); on[ok] = m[i[ok], j[ok]]
                if on.sum() >= 30:
                    grid[b + k, a + k] = li[on].mean(); cnt[b + k, a + k] = on.sum()
        if np.isnan(grid).all():
            continue
        bi, bj = np.unravel_index(np.nanargmax(grid), grid.shape); peak = float(grid[bi, bj]); base = float(np.nanmedian(grid)); n_at = int(cnt[bi, bj])
        dE = -(bj - k) * st; dN = -(bi - k) * st          # the lidar was moved by (+a, +b) onto the paint: the paint sits at -(a, b) from the lidar
        ok = n_at >= Q['MIN_RETURNS'] and peak - base >= Q['MIN_CONTRAST']
        rows.append({'tile': t['id'], 'measured_paint_items': n_it, 'returns_on_paint_at_peak': n_at, 'peak_minus_median_dlog': round(peak - base, 2),
                     'aerial_minus_lidar_m': [round(dE, 2), round(dN, 2)], 'offset_m': round(math.hypot(dE, dN), 2), 'reported': ok,
                     'at_the_edge_of_the_search': bool(bi in (0, 2 * k) or bj in (0, 2 * k))})
        print(rows[-1], flush=True)
    rep = [r for r in rows if r['reported'] and not r['at_the_edge_of_the_search']]; off = np.array([r['offset_m'] for r in rep]) if rep else np.zeros(0)
    vec = np.array([r['aerial_minus_lidar_m'] for r in rep]) if rep else np.zeros((0, 2))
    out = {'_doc': ' '.join(__doc__.strip().split('\n\n')[2].split()), 'thresholds_invented': Q, 'tiles_tried': len(rows), 'tiles_reported': len(rep),
           'offset_m_p50_p84_p95': [round(float(v), 2) for v in np.percentile(off, [50, 84, 95])] if len(off) else None,
           'mean_aerial_minus_lidar_m': [round(float(v), 2) for v in vec.mean(0)] if len(vec) else None, 'tiles': rows}
    os.makedirs(os.path.join(HERE, 'refutation'), exist_ok=True)
    json.dump(out, open(os.path.join(HERE, 'refutation', 'paint_registration.json'), 'w'), indent=1)
    print({k: v for k, v in out.items() if k != 'tiles'})


if __name__ == '__main__':
    main(sys.argv[1])

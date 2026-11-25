"""Paint on one work tile of the lap, all three flight years, in one frame (stage 1 of the lap's paint survey).

    python3 paint_tile.py <cache-dir> [tile-id ...]          # all tiles when none is named; 3 processes

Per tile and year the pilot's reader (paint_read.read) runs inside the lap's corridor with the 2020 lidar beside it.
Then, in the 2022 picture's pixel grid (the three years share the archive's grid; the shift between years is measured per
tile by correlating their paint and applied):

  seen      each 2022 mark is looked for in 2020 and 2018: 'seen' (paint under at least half of it), 'hidden' (a vehicle,
            deep shadow or off the flooded roadway there), or 'absent' (bare pavement where it lies: painted since);
  replaced  a 2020 / 2018 mark that covers a 2022 mark and is at least REPL_RATIO longer, the rest of it hidden in 2022,
            takes its place (geometry from the older year, seen in both): a dash half under a car in 2022;
  filled    a 2020 / 2018 mark with no 2022 mark under it is added with what 2022 shows there: 'hidden' (it fills),
            'rejected' (2022 has paint there the reader dropped) or 'absent' (bare pavement in 2022: possibly removed).

Width model (the pilot over-read thin lines): the mark's mean luminance profile across its width is fitted with a box of
width w blurred by a Gaussian of sigma s (the picture's point spread, pixel included). Wide bars give s (their edges);
for thin marks s is fixed at the year's median from the bars and w, contrast and centre are fitted. 'width_fit_m' is w;
'width_read_m' stays the pilot's area / length.

Writes <cache>/paint/<tile-id>.pkl: marks in ENU metres (lapgeo's frame) with their year, seen-states, lidar check,
widths; the white blobs left after lines, dashes and bars (for symbol typing); per-year stats. No inventory is written
here: paint_lap.py assembles the lap.
"""
import json, math, os, pickle, sys, time
import numpy as np
from scipy import ndimage, optimize, special

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import lapgeo, paint_read as pr, prep  # noqa: E402
from scripts.aerial.engine import channels  # noqa: E402

YEARS = (2022, 2020, 2018)
Q = {'SEEN_MIN': 0.5, 'HID_MIN': 0.3, 'FILL_OV_MAX': 0.3, 'REPL_RATIO': 1.3, 'SUPPORT_DIL_PX': 2, 'KEPT_DIL_PX': 3, 'PROFILE_HALF_M': 1.3,
     'BLOB_JOIN_M': 0.2, 'BLOB_AREA_M2': (0.25, 6.0), 'BLOB_BOX_M': (0.7, 8.0), 'SHIFT_MAX_PX': 8, 'EDGE_M': 0.6, 'EDGE_PROBE_M': 0.9, 'EDGE_DLUM': 25.0}


def corridor(ortho):
    ys, xs = np.mgrid[0:ortho.H:8, 0:ortho.W:8]; E, N = ortho.px_to_en(xs.ravel().astype(float), ys.ravel().astype(float))
    _, d, _ = lapgeo.where(E, N); m = (d <= lapgeo.CORRIDOR_M).reshape(ys.shape)
    return np.kron(m, np.ones((8, 8), bool))[:ortho.H, :ortho.W]


def box_profile(x, bg, C, w, s, x0):
    k = 1.0 / (math.sqrt(2) * max(s, 1e-3))
    return bg + 0.5 * C * (special.erf((x - x0 + w / 2) * k) - special.erf((x - x0 - w / 2) * k))


def profile(lum, m, gsd):
    """mean luminance across the mark: samples every quarter pixel along the normal at each centre-line point"""
    cl = m['cl'] if len(m['cl']) > 1 else np.array([m['c']]); nrm = np.array([-m['ax'][1], m['ax'][0]])
    if len(cl) > 2:                                                # the local normal of a curved line
        tg = np.gradient(cl, axis=0); tg /= np.maximum(np.hypot(*tg.T)[:, None], 1e-6); nr = np.stack([-tg[:, 1], tg[:, 0]], 1)
    else:
        nr = np.repeat(nrm[None], len(cl), 0)
    t = np.arange(-Q['PROFILE_HALF_M'], Q['PROFILE_HALF_M'] + 1e-6, 0.25 * gsd)
    X = cl[:, 0][:, None] + nr[:, 0][:, None] * t[None] / gsd; Y = cl[:, 1][:, None] + nr[:, 1][:, None] * t[None] / gsd
    v = ndimage.map_coordinates(lum, [Y, X], order=1, mode='nearest')
    return t, np.median(v, 0) if len(cl) >= 3 else v.mean(0)


def fit_width(t, p, sigma=None):
    """box-blur fit. sigma None: fitted too (wide marks). Returns (w, sigma, contrast, rms) or None."""
    side = np.abs(t) > 0.8; bg = float(np.median(p[side])); pk = float(p[np.abs(t) < 0.5].max()) - bg
    if pk < 8:
        return None
    half = p - bg > pk / 2; c0 = float(np.average(t[half], weights=(p - bg)[half])) if half.any() else 0.0
    w0 = max(0.05, float(half.sum()) * (t[1] - t[0])); sel = np.abs(t - c0) < max(0.6, w0 / 2 + 0.45)
    try:
        if sigma is None:
            r = optimize.least_squares(lambda q: box_profile(t[sel], q[0], q[1], q[2], q[3], q[4]) - p[sel], [bg, pk, w0, 0.06, c0],
                                       bounds=([0, 1, 0.02, 0.02, c0 - 0.3], [255, 400, 2.0, 0.25, c0 + 0.3]))
            return float(r.x[2]), float(r.x[3]), float(r.x[1]), float(np.sqrt(np.mean(r.fun ** 2)))
        r = optimize.least_squares(lambda q: box_profile(t[sel], q[0], q[1], q[2], sigma, q[3]) - p[sel], [bg, max(pk, 20) * 1.3, min(w0, 0.15), c0],
                                   bounds=([0, 1, 0.02, c0 - 0.3], [255, 400, 2.0, c0 + 0.3]))
        return float(r.x[2]), sigma, float(r.x[1]), float(np.sqrt(np.mean(r.fun ** 2)))
    except Exception:           # noqa: BLE001
        return None


def shift_between(a, b, mx):
    """integer (dx, dy) that moves mask b onto mask a (a[y, x] ~ b[y - dy, x - dx]), by correlation; (0, 0) when weak"""
    f = 2; A = a[::f, ::f].astype(np.float32); Bm = b[::f, ::f].astype(np.float32)
    if A.sum() < 500 or Bm.sum() < 500:
        return 0, 0, 0.0
    A = ndimage.gaussian_filter(A, 1.0); Bm = ndimage.gaussian_filter(Bm, 1.0)
    c = np.fft.irfft2(np.fft.rfft2(A) * np.conj(np.fft.rfft2(Bm)), A.shape); r = mx // f + 1
    c = np.roll(np.roll(c, r, 0), r, 1)[:2 * r + 1, :2 * r + 1]; iy, ix = np.unravel_index(np.argmax(c), c.shape)
    # refine at full resolution about the coarse peak
    best = (0, 0, -1.0); a8 = a;
    for dy in range((iy - r) * f - 2, (iy - r) * f + 3):
        for dx in range((ix - r) * f - 2, (ix - r) * f + 3):
            sb = np.roll(np.roll(b, dy, 0), dx, 1); v = float((a8 & sb).sum())
            if v > best[2]:
                best = (dx, dy, v)
    return best[0], best[1], best[2] / max(1.0, min(a.sum(), b.sum()))


def at(mask, ys, xs, dx=0, dy=0):
    y = np.clip(ys - dy, 0, mask.shape[0] - 1); x = np.clip(xs - dx, 0, mask.shape[1] - 1)
    return mask[y, x]


def to_en(ortho, m, year, gsd):
    def en(p):
        p = np.atleast_2d(np.asarray(p, float)); E, N = ortho.px_to_en(p[:, 0], p[:, 1]); return np.stack([E, N], 1)
    ends = en(np.array(m['ends'])); cl = en(m['cl']) if len(m['cl']) else ends; c = en(m['c'])[0]
    d = ends[1] - ends[0]; n = np.hypot(*d)
    if n < 1e-6:
        d = np.array([1.0, 0.0]); n = 1.0
    out = {'year': year, 'colour': m['colour'], 'kind': m['kind'], 'double': bool(m.get('double')), 'c': c, 'ax': d / n, 'ends': ends, 'cl': cl,
           'L': float(m['L']), 'W': float(m['W']), 'Wmed': float(m['Wmed']), 'area': float(m['area']), 'shadow': bool(m['shadow']), 'lum': m['lum'],
           'side_lum': m['side_lum'], 'bearing': float(math.degrees(math.atan2(d[0], d[1])) % 180.0)}
    for k in ('lidar_n', 'lidar_dlog', 'lidar_confirms', 'wfit', 'wsig', 'wcon', 'wrms'):
        if k in m:
            out[k] = m[k]
    return out


def run(tid, cache):
    out = os.path.join(cache, 'paint', tid + '.pkl'); os.makedirs(os.path.dirname(out), exist_ok=True)
    lid = os.path.join(cache, 'lidar', tid + '.npz'); Y = {}; t0 = time.time(); pre = {}

    class Shim:
        gsd = (0.0762, 0.0762)
    for y in YEARS:                                     # shadow gain and the coloured surfaces first: 'coloured' needs two years
        img = os.path.join(cache, 'img', str(y), tid + '.png')
        if os.path.exists(img):
            from PIL import Image
            o = Shim(); o.rgb = np.asarray(Image.open(img).convert('RGB')).astype(np.float32)
            if o.rgb.max() == 0:
                continue
            g = prep.shadow_gain(o, 0.0762); g['rgb'] = o.rgb; g['col'] = prep.coloured(o.rgb, 0.0762); pre[y] = g
    stable = {}
    for name in ('red', 'green'):
        n = sum(pre[y]['col'][name].astype(np.uint8) for y in pre) if pre else 0
        stable[name] = ndimage.binary_dilation(n >= 2, iterations=4) if len(pre) >= 2 else np.zeros((1, 1), bool)
    for y in YEARS:
        img = os.path.join(cache, 'img', str(y), tid + '.png')
        if y not in pre:
            continue

        def prepare(ortho, y=y):
            ortho.rgb = pre[y]['rgb']; ex = np.zeros(ortho.rgb.shape[:2], bool)
            for name in ('red', 'green'):
                if stable[name].shape == ex.shape:
                    ex |= pre[y]['col'][name] & stable[name]
            pre[y]['road_extra'] = ex
            return {'mask_out': pre[y]['mask_out'], 'road_extra': ex}
        ortho, gsd, marks, stats, masks = pr.read(img, lid if os.path.exists(lid) else None, corridor=corridor, prepare=prepare)
        white, yellow, win, covered, dark, top, ytop = masks
        shadow = pre[y]['shadow']
        for m in marks:
            m['shadow'] = bool(shadow[m['pix']].mean() > 0.5)
        stats['roadway_in_shadow_share'] = round(float((shadow & win).sum()) / max(float(win.sum()), 1.0), 3)
        lum = ortho.rgb @ np.array([0.299, 0.587, 0.114], np.float32)
        # the roadway's edge: a long white mark within EDGE_M of the flooded roadway's rim whose two sides, EDGE_PROBE_M out,
        # differ by EDGE_DLUM is the gutter's lip or the kerb, not paint (asphalt one side, concrete the other)
        din = ndimage.distance_transform_edt(win) * gsd; lsm = ndimage.gaussian_filter(lum, 2.0); keepm = []; nk = 0
        for m in marks:
            if m['colour'] == 'white' and m['L'] > 3.0 and m['kind'] in ('line', 'bar', 'dash') and len(m['cl']) >= 3:
                cl = m['cl']; dmed = float(np.median(channels.sample(din, cl[:, 0], cl[:, 1])))
                if dmed < Q['EDGE_M']:
                    nrm = np.array([-m['ax'][1], m['ax'][0]]); off = (Q['EDGE_PROBE_M'] + m['Wmed'] / 2) / gsd
                    la = np.median(channels.sample(lsm, cl[:, 0] + nrm[0] * off, cl[:, 1] + nrm[1] * off)); lb = np.median(channels.sample(lsm, cl[:, 0] - nrm[0] * off, cl[:, 1] - nrm[1] * off))
                    if abs(float(la) - float(lb)) > Q['EDGE_DLUM']:
                        nk += 1; continue
            keepm.append(m)
        marks = keepm; stats['dropped']['along_the_roadway_edge'] = nk
        # widths: sigma from the wide marks of this tile and year, then every mark
        sig = []
        for m in marks:
            if m['kind'] in ('block', 'bar') and m['colour'] == 'white':
                t, p = profile(lum, m, gsd); f = fit_width(t, p)
                if f and f[0] > 0.3 and f[3] < 0.12 * f[2]:
                    sig.append(f[1]); m.update(wfit=f[0], wsig=f[1], wcon=f[2], wrms=f[3])
        Y[y] = {'ortho': ortho, 'gsd': gsd, 'marks': marks, 'stats': stats, 'white': white, 'yellow': yellow, 'win': win, 'lum': lum,
                'hid': ndimage.binary_dilation(covered, iterations=3) | dark | ~win | shadow, 'covered': covered, 'shadow': shadow, 'sig': sig,
                'col': {n: pre[y]['col'][n] & stable[n] if stable[n].shape == shadow.shape else np.zeros_like(shadow) for n in ('red', 'green')}}
    if 2022 not in Y:
        return tid, 'no 2022 image'
    return tid, Y, out, t0


def finish(tid, Y, out, t0, sigma):
    """second pass once the lap's sigma per year is known: thin-mark widths, cross-year states, blobs, pickle"""
    R = Y[2022]; H, W = R['white'].shape; gsd = R['gsd']; res = {'tile': tid, 'years': sorted(Y), 'stats': {y: Y[y]['stats'] for y in Y}, 'shift_px': {}, 'sigma_m': sigma}
    for y in Y:
        for m in Y[y]['marks']:
            if 'wfit' not in m and m['kind'] != 'symbol':
                t, p = profile(Y[y]['lum'], m, Y[y]['gsd']); f = fit_width(t, p, sigma[y])
                if f:
                    m.update(wfit=f[0], wsig=f[1], wcon=f[2], wrms=f[3])
    paint = {y: ndimage.binary_dilation(Y[y]['white'] | Y[y]['yellow'], iterations=Q['SUPPORT_DIL_PX']) for y in Y}
    sh = {2022: (0, 0)}
    for y in Y:
        if y != 2022:
            dx, dy, sc = shift_between(R['white'] | R['yellow'], Y[y]['white'] | Y[y]['yellow'], Q['SHIFT_MAX_PX'])
            sh[y] = (dx, dy); res['shift_px'][y] = {'dx': dx, 'dy': dy, 'overlap_share': round(sc, 3)}

    def state(ys, xs, y, frm):
        """what year y shows under pixels given in year frm's grid"""
        dx = sh[frm][0] - sh[y][0]; dy = sh[frm][1] - sh[y][1]                       # frm -> 2022 -> y
        sup = float(at(paint[y], ys, xs, -dx, -dy).mean()); hid = float(at(Y[y]['hid'], ys, xs, -dx, -dy).mean())
        if sup >= Q['SEEN_MIN']:
            return 'seen', sup, hid
        if hid >= Q['HID_MIN'] and sup + hid >= 0.7:
            return 'hidden', sup, hid
        return 'absent', sup, hid

    kept = []                                                                     # (year, mark)
    for m in R['marks']:
        m['seen'] = {2022: 'seen'}
        for y in Y:
            if y != 2022:
                st, sup, hid = state(*m['pix'], y, 2022); m['seen'][y] = st
        kept.append((2022, m))
    idr = np.zeros((H, W), np.int32)
    for k, (_, m) in enumerate(kept, 1):
        idr[m['pix']] = k
    idd = ndimage.grey_dilation(idr, size=(2 * Q['KEPT_DIL_PX'] + 1,) * 2)
    dead = set(); counts = {'replaced': 0, 'filled_hidden': 0, 'filled_rejected': 0, 'older_only_absent_in_2022': 0}
    for y in [v for v in YEARS if v in Y and v != 2022]:
        dx, dy = sh[y]
        for m in Y[y]['marks']:
            ys, xs = m['pix']; y2 = np.clip(ys + dy, 0, H - 1); x2 = np.clip(xs + dx, 0, W - 1)                      # into the 2022 grid
            under = idd[y2, x2]; ov = float((under > 0).mean())
            m['seen'] = {y: 'seen'}
            for yy in Y:
                if yy != y:
                    m['seen'][yy] = state(ys, xs, yy, y)[0]
            if ov >= Q['FILL_OV_MAX']:
                ids = [i for i in np.unique(under[under > 0]) if i not in dead]
                olds = [kept[i - 1] for i in ids]
                if (m['kind'] in ('line', 'dash', 'block', 'bar') and olds and all(o[1]['kind'] == olds[0][1]['kind'] or o[1]['kind'] in ('symbol', 'dash') for o in olds)
                        and all(o[0] == 2022 for o in olds) and m['L'] >= Q['REPL_RATIO'] * max(o[1]['L'] for o in olds)):
                    extra = under == 0
                    if extra.any() and float(R['hid'][y2[extra], x2[extra]].mean()) >= 0.5:
                        # every old mark must lie mostly inside the new one
                        mine = np.zeros((H, W), bool); mine[y2, x2] = True; mine = ndimage.binary_dilation(mine, iterations=Q['KEPT_DIL_PX'])
                        if all(float(mine[o[1]['pix']].mean()) >= 0.6 for o in olds):
                            for i in ids:
                                dead.add(i)
                            m['seen'][2022] = 'partly (the rest hidden)'; m['replaces_2022_pieces'] = len(ids)
                            if any(o[1].get('lidar_confirms') for o in olds) and 'lidar_confirms' not in m:
                                m['lidar_confirms'] = True
                            kept.append((y, m)); idr[y2, x2] = len(kept); idd = ndimage.grey_dilation(idr, size=(2 * Q['KEPT_DIL_PX'] + 1,) * 2)
                            counts['replaced'] += 1
                continue
            hid22 = float(R['hid'][y2, x2].mean()); sup22 = float(paint[2022][y2, x2].mean())
            if sup22 >= Q['SEEN_MIN']:
                m['seen'][2022] = 'rejected (paint is there in 2022; its reader dropped the mark)'; counts['filled_rejected'] += 1
            elif hid22 >= 0.4:
                m['seen'][2022] = 'hidden'; counts['filled_hidden'] += 1
            else:
                m['seen'][2022] = 'absent'; counts['older_only_absent_in_2022'] += 1
            kept.append((y, m)); idr[y2, x2] = len(kept); idd = ndimage.grey_dilation(idr, size=(2 * Q['KEPT_DIL_PX'] + 1,) * 2)
    marks = []
    for k, (y, m) in enumerate(kept, 1):
        if k in dead:
            continue
        e = to_en(Y[y]['ortho'], m, y, Y[y]['gsd']); e['seen'] = m['seen']
        if y != 2022:                                                              # the measured shift, so all years sit in 2022's frame
            d = np.array([sh[y][0], -sh[y][1]]) * gsd; e['c'] = e['c'] + d; e['ends'] = e['ends'] + d; e['cl'] = e['cl'] + d
        if 'replaces_2022_pieces' in m:
            e['replaces_2022_pieces'] = m['replaces_2022_pieces']
        e['edge'] = bool(m['pix'][0].min() <= 1 or m['pix'][1].min() <= 1 or m['pix'][0].max() >= H - 2 or m['pix'][1].max() >= W - 2)
        if m['kind'] in ('symbol', 'dash', 'block'):                               # the shape, for typing: a small mask in the mark's year
            ys, xs = m['pix']; e['patch_px0'] = (int(xs.min()), int(ys.min()))
            pm = np.zeros((ys.max() - ys.min() + 1, xs.max() - xs.min() + 1), bool); pm[ys - ys.min(), xs - xs.min()] = True; e['patch'] = np.packbits(pm, axis=1); e['patch_shape'] = pm.shape
        marks.append(e)
    # blobs: the white left in each year's picture once long lines are taken out, joined across small gaps (letters, arrow parts)
    blobs = []
    for y in Y:
        o = Y[y]['ortho']; wm = Y[y]['white'].copy()
        for m in Y[y]['marks']:
            if m['kind'] == 'line' or (m['kind'] == 'bar' and m['L'] > 6.0):
                wm[m['pix']] = False
        j = max(1, int(round(Q['BLOB_JOIN_M'] / 2 / gsd))); lab, n = ndimage.label(ndimage.binary_dilation(wm, iterations=j))
        lab = lab * wm
        for i, sl in enumerate(ndimage.find_objects(lab), 1):
            if sl is None:
                continue
            h = (sl[0].stop - sl[0].start) * gsd; w = (sl[1].stop - sl[1].start) * gsd
            if not (Q['BLOB_BOX_M'][0] <= max(h, w) <= Q['BLOB_BOX_M'][1]):
                continue
            pm = lab[sl] == i; a = float(pm.sum()) * gsd * gsd
            if not (Q['BLOB_AREA_M2'][0] <= a <= Q['BLOB_AREA_M2'][1]):
                continue
            ys, xs = np.nonzero(pm); cy = ys.mean() + sl[0].start; cx = xs.mean() + sl[1].start
            if Y[y]['hid'][int(cy), int(cx)] and float(Y[y]['hid'][ys + sl[0].start, xs + sl[1].start].mean()) > 0.5:
                continue
            E, N = o.px_to_en(np.array([cx, float(sl[1].start), float(sl[1].stop)]), np.array([cy, float(sl[0].stop), float(sl[0].start)]))
            d = np.array([sh[y][0], -sh[y][1]]) * gsd if y != 2022 else np.zeros(2)
            blobs.append({'year': y, 'c': np.array([E[0], N[0]]) + d, 'box_en': [E[1] + d[0], N[1] + d[1], E[2] + d[0], N[2] + d[1]], 'area': a,
                          'patch': np.packbits(pm, axis=1), 'patch_shape': pm.shape, 'gsd': gsd,
                          'edge': bool(sl[0].start <= 1 or sl[1].start <= 1 or sl[0].stop >= H - 1 or sl[1].stop >= W - 1)})
    surfaces = []
    for name in ('red', 'green'):
        ys_ = [y for y in Y if Y[y]['col'][name].any()]
        if len(ys_) < 2:
            continue
        n = sum(Y[y]['col'][name].astype(np.uint8) for y in ys_); lab, k = ndimage.label(n >= 1)
        for i, sl in enumerate(ndimage.find_objects(lab), 1):
            pm = lab[sl] == i; a = float(pm.sum()) * gsd * gsd
            if a < prep.Q['COL_MIN_M2'] or float((n[sl][pm] >= 2).mean()) < 0.3:
                continue
            yrs = [y for y in ys_ if float(Y[y]['col'][name][sl][pm].mean()) > 0.3]
            if len(yrs) < 2:
                continue
            pad = 8; s2 = (slice(max(0, sl[0].start - pad), sl[0].stop + pad), slice(max(0, sl[1].start - pad), sl[1].stop + pad))
            comp = lab[s2] == i; ring = ndimage.binary_dilation(comp, iterations=7) & ~ndimage.binary_dilation(comp, iterations=1)
            anycol = sum(Y[y]['col'][c2][s2] for y in ys_ for c2 in ('red', 'green')) > 0
            ring_road = float((R['win'][s2] & ~anycol)[ring].mean()) if ring.any() else 0.0
            yb = 2022 if 2022 in yrs else yrs[0]; rgbm = Y[yb]['ortho'].rgb[sl][pm & Y[yb]['col'][name][sl]].mean(0)
            E, N = R['ortho'].px_to_en(np.array([float(sl[1].start), float(sl[1].stop)]), np.array([float(sl[0].stop), float(sl[0].start)]))
            surfaces.append({'colour': name, 'area': a, 'ring_road': ring_road, 'years': yrs, 'rgb': [float(v) for v in rgbm], 'px0': (sl[1].start, sl[0].start), 'patch': np.packbits(pm, axis=1), 'patch_shape': pm.shape,
                             'box_en': [float(E[0]), float(N[0]), float(E[1]), float(N[1])],
                             'edge': bool(sl[0].start <= 1 or sl[1].start <= 1 or sl[0].stop >= H - 1 or sl[1].stop >= W - 1)})
    res['surfaces'] = surfaces; res['bbox_ftus'] = R['ortho'].desc.get('bbox_ftus') if isinstance(R['ortho'].desc, dict) else None
    res.update(marks=marks, blobs=blobs, counts=counts, seconds=round(time.time() - t0, 1))
    # coverage per year on a 1 m grid in ENU, for 'what could not be read': roadway, hidden (vehicle / shadow)
    cov = {}
    for y in Y:
        o = Y[y]['ortho']; f = 13; h2, w2 = H // f, W // f
        def blk(a):
            return a[:h2 * f, :w2 * f].reshape(h2, f, w2, f).mean((1, 3))
        ys, xs = np.mgrid[0:h2, 0:w2]; E, N = o.px_to_en((xs.ravel() * f + f / 2).astype(float), (ys.ravel() * f + f / 2).astype(float))
        cov[y] = {'E': E.astype(np.float32), 'N': N.astype(np.float32), 'road': blk(Y[y]['win']).ravel().astype(np.float32),
                  'hid': blk(Y[y]['hid'] & Y[y]['win']).ravel().astype(np.float32), 'veh': blk(Y[y]['covered'] & Y[y]['win']).ravel().astype(np.float32),
                  'shadow': blk(Y[y]['shadow'] & Y[y]['win']).ravel().astype(np.float32), 'cell_m2': (f * gsd) ** 2}
    res['coverage'] = cov
    os.makedirs(os.path.join(os.path.dirname(os.path.dirname(out)), 'masks'), exist_ok=True)      # for the post reader: roadway, vehicles, shadow
    for y in Y:
        np.savez_compressed(os.path.join(os.path.dirname(os.path.dirname(out)), 'masks', f'{tid}_{y}.npz'), shape=np.array(Y[y]['win'].shape),
                            win=np.packbits(Y[y]['win']), covered=np.packbits(Y[y]['covered']), shadow=np.packbits(Y[y]['shadow']))
    pickle.dump(res, open(out, 'wb'))
    return tid, len(marks), counts, res['shift_px'], res['seconds']


def one(args):
    tid, cache, sigma = args
    r = run(tid, cache)
    if len(r) == 2:
        return r
    tid, Y, out, t0 = r
    if sigma is None:                                   # sigma pass: only the wide marks' fits
        return tid, {y: Y[y]['sig'] for y in Y}
    return finish(tid, Y, out, t0, sigma)


if __name__ == '__main__':
    import multiprocessing as mp
    cache = sys.argv[1]; ids = sys.argv[2:] or [t['id'] for t in lapgeo.tiles()]
    sp = os.path.join(cache, 'paint', 'sigma.json'); os.makedirs(os.path.dirname(sp), exist_ok=True)
    if os.path.exists(sp):
        sigma = {int(k): v for k, v in json.load(open(sp))['sigma_m'].items()}
    else:                                               # the point spread per year from a spread of tiles' wide marks
        some = [t['id'] for t in lapgeo.tiles()][::4]
        with mp.Pool(3) as pool:
            rs = pool.map(one, [(t, cache, None) for t in some])
        allsig = {}
        for r in rs:
            if isinstance(r[1], dict):
                for y, v in r[1].items():
                    allsig.setdefault(y, []).extend(v)
        sigma = {y: float(np.median(v)) for y, v in allsig.items()}
        json.dump({'_doc': 'Gaussian sigma (m) of the picture\'s point spread per flight year: the median over wide white bars\' fitted edges on every 4th work tile',
                   'sigma_m': sigma, 'bars_fitted': {y: len(v) for y, v in allsig.items()}, 'p16_p84': {y: [float(a) for a in np.percentile(v, [16, 84])] for y, v in allsig.items()}}, open(sp, 'w'), indent=1)
    print('sigma', sigma, flush=True)
    with mp.Pool(3) as pool:
        for r in pool.imap_unordered(one, [(t, cache, sigma) for t in ids]):
            print(r, flush=True)

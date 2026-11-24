"""Post candidates on one work tile from their shadows, each flight year on its own (stage 1 of the lap's post survey).

    python3 posts_tile.py <cache-dir> [tile-id ...]        # after paint_tile.py (it writes the roadway / shadow masks)

The pilot's reader (strokes_read.py) with what the pilot found wanting:

  sun       FIRST PASS: the shadow's bearing is searched only within SUN_WIN_DEG of the year's bearing read by eye at Speer / Lawrence
            (PRIOR: in 2020 the shadows run north-west, ALONG the downtown grid, so "away from the grid" cannot find it);
            per tile it is the weighted median of the long thin strokes in that window, the prior when they are too few.
            SECOND PASS (--known): the bearing per tile and year comes from the feet the eye confirmed (sun_from_posts);
  dark      a shadow is DARK_REL of its sunlit background darker (at least DARK_MIN): the 2020 lawns are green and dark,
            and a fixed step lost every lamp standing on grass;
  shadow    nothing is read inside a building's shadow (prep.shadow_mask): a post there casts none. Counted per year;
  foot      base = the sun-ward end of the stroke. foot_bright = how far the brightest spot within FOOT_R of the base stands
            over its surroundings: a lamp's head seen from above sits at the foot of its own shadow;
  crown     tip_mass = dark area within TIP_R of the far end that is not the stroke: a bare tree's trunk ends in a tangle
            of branch shadows, a post's shadow ends clean or in one head;
  arms      strokes of another bearing that leave the post's shadow (the arm's shadow, part-way up) or its base (the arm
            itself: these pictures are not true orthophotos of things above the ground);
  clutter   the share of dark pixels in bands 0.55 and 0.9 m beside the stroke: a branch's shadow lies among others;
  road      base on the flooded roadway (paint stage), more than ROAD_IN_M inside it: a vehicle's edge or a mark;
A stroke is a candidate, never a post: posts_lap.py joins the years and the eye decides.
"""
import math, os, pickle, sys, time
import numpy as np
import cv2
from scipy import ndimage
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import lapgeo, paint_read as pr, prep, strokes_read as sr  # noqa: E402
from scripts.aerial.engine.ortho import Ortho  # noqa: E402

YEARS = (2022, 2020, 2018)
PRIOR = {2022: 358.0, 2020: 312.0, 2018: 0.0}            # compass bearing base -> tip of a post's shadow, by eye
P = {'HAT_M': 1.6, 'DARK_MIN': 16.0, 'DARK_REL': 0.28, 'BG_MIN': 55.0, 'LINE_M': 1.1, 'POST_L_MIN': 1.8, 'POST_W_MAX': 0.75, 'ARM_L_MIN': 1.8, 'ARM_W_MAX': 0.9, 'ARM_JOIN': 1.0,
     'SUN_WIN_DEG': 14.0, 'SUN_KNOWN_MIN': 3, 'SUN_KNOWN_GOOD': 4, 'SUN_PLAUSIBLE_DEG': 20.0, 'SUN_MIN_VOTE_M': 20.0, 'FOOT_R': 0.6, 'TIP_R': 2.2, 'ROAD_IN_M': 0.6, 'SHADOW_PAD_M': 0.4}


def unpack(z, k):
    return np.unpackbits(z[k])[:int(z['shape'][0]) * int(z['shape'][1])].reshape(tuple(z['shape'])).astype(bool)


def sun_from_posts(dark, ortho, gsd, known):
    """The shadow bearing of this tile and year from posts whose feet are already known (confirmed by eye in the first
    pass): from each foot, the ray (0.6 to 3.5 m out, every 3 degrees) that lies most in the dark mask; the tile's bearing
    is the mean of the votes within 6 degrees of the fullest 6-degree bin, if at least SUN_KNOWN_MIN posts vote there.
    The first pass used one bearing per year read by eye at one place; the 2020 flight turned out to hold flight lines of
    different hours (its shadows fall north-east, not north-west, east of Sherman), so the year's bearing is not one number."""
    dd = ndimage.binary_dilation(dark, iterations=3); H, W = dark.shape; votes = []; r = np.arange(0.6, 3.5, gsd) / gsd
    for E, N in known:
        x, y = ortho.en_to_px(np.array([E]), np.array([N])); x, y = float(x[0]), float(y[0])
        if not (50 <= x < W - 50 and 50 <= y < H - 50):
            continue
        best = (0.0, None)
        for b in range(0, 360, 3):
            a = math.radians(b); xs = np.round(x + r * math.sin(a)).astype(int); ys = np.round(y - r * math.cos(a)).astype(int)
            f = float(dd[ys, xs].mean())
            if f > best[0]:
                best = (f, b)
        if best[0] >= 0.7:
            votes.append(best[1])
    if len(votes) < P['SUN_KNOWN_MIN']:
        return None, len(votes)
    v = np.array(votes, float); hist = np.array([np.sum(np.abs((v - c + 180) % 360 - 180) <= 6) for c in range(0, 360, 3)]); c = float(np.argmax(hist) * 3)
    sel = np.abs((v - c + 180) % 360 - 180) <= 6
    if sel.sum() < P['SUN_KNOWN_MIN']:
        return None, len(votes)
    return float((c + np.mean((v[sel] - c + 180) % 360 - 180)) % 360.0), int(sel.sum())


def run(tid, cache, known=None, fallback=None):
    t0 = time.time(); out = {'tile': tid, 'years': {}}
    for y in YEARS:
        img = os.path.join(cache, 'img', str(y), tid + '.png'); mk = os.path.join(cache, 'masks', f'{tid}_{y}.npz')
        if not os.path.exists(img) or not os.path.exists(mk):
            continue
        ortho = Ortho.load(img, origin=lapgeo.ORIGIN); gsd = float(np.mean(ortho.gsd)); z = np.load(mk)
        win = unpack(z, 'win'); bsh = unpack(z, 'shadow'); cov = unpack(z, 'covered')
        lum0 = ortho.rgb.mean(-1); lum = ndimage.gaussian_filter(lum0, 0.6); k = max(3, int(round(P['HAT_M'] / gsd)) | 1)
        bg = cv2.morphologyEx(lum.astype(np.float32), cv2.MORPH_CLOSE, np.ones((k, k), np.uint8)); bh = bg - lum
        dark = (bh >= np.maximum(P['DARK_MIN'], P['DARK_REL'] * bg)) & (bg >= P['BG_MIN']) & ~ndimage.binary_dilation(bsh, iterations=int(P['SHADOW_PAD_M'] / gsd))
        def lopen(m_, length_m, bearing):
            return cv2.morphologyEx(m_.astype(np.uint8), cv2.MORPH_OPEN, sr.line_fp(length_m / gsd, bearing).astype(np.uint8)).astype(bool)
        # the year's bearing here: from known posts when given (second pass), else the prior read by eye
        prior = PRIOR[y]; cal = None
        if known is not None:
            cal, nv = sun_from_posts(dark, ortho, gsd, known)
            prior = cal if cal is not None else (fallback or {}).get(y, PRIOR[y])
        # strokes within about 13 degrees of that bearing (three openings), then the tile's own bearing from the long thin ones
        along = lopen(dark, P['LINE_M'], (prior - 9) % 180.0) | lopen(dark, P['LINE_M'], prior % 180.0) | lopen(dark, P['LINE_M'], (prior + 9) % 180.0)
        cand = sr.strokes(along, gsd, 3.0, 0.45); pr0 = prior % 180.0
        dv = np.array([(m['bearing'] - pr0 + 90) % 180 - 90 for m in cand]); Ls = np.array([m['L'] for m in cand]); near = np.abs(dv) < P['SUN_WIN_DEG'] if len(dv) else np.zeros(0, bool)
        if near.any() and Ls[near].sum() >= P['SUN_MIN_VOTE_M']:
            o_ = np.argsort(dv[near]); cw = np.cumsum(Ls[near][o_]); med = dv[near][o_][int(np.searchsorted(cw, cw[-1] / 2))]
            sun = (prior + float(med)) % 360.0; votes = float(Ls[near].sum())
        else:
            sun = prior; votes = 0.0
        posts = sr.strokes(along, gsd, P['POST_L_MIN'], P['POST_W_MAX'])
        rest = dark & ~ndimage.binary_dilation(along, iterations=1); arms = []
        for ab in range(0, 180, 10):
            if abs((ab - sun + 90) % 180 - 90) < 12:
                continue
            for m in sr.strokes(lopen(rest, 1.6, ab), gsd, P['ARM_L_MIN'], P['ARM_W_MAX']):
                if abs((m['bearing'] - ab + 90) % 180 - 90) <= 6:
                    arms.append(m)
        dsh = np.array([math.sin(math.radians(sun)), -math.cos(math.radians(sun))])           # base -> tip in pixels (y down)
        road_in = ndimage.binary_erosion(win, iterations=int(P['ROAD_IN_M'] / gsd)); lab_al, _ = ndimage.label(along, structure=np.ones((3, 3)))
        rf = int(P['FOOT_R'] / gsd); rt = int(P['TIP_R'] / gsd); H, W = lum.shape; rows = []
        for m in posts:
            e0, e1 = m['ends']; base, tip = (e0, e1) if (e1 - e0) @ dsh > 0 else (e1, e0)
            v = (tip - base) * gsd; Lm = float(np.hypot(*v)); u = v / max(Lm, 1e-6); bx, by = int(round(base[0])), int(round(base[1])); tx, ty = int(round(tip[0])), int(round(tip[1]))
            if not (rt <= bx < W - rt and rt <= by < H - rt and rt <= tx < W - rt and rt <= ty < H - rt):
                edge = True
            else:
                edge = False
            def win_(a, cx, cy, r):
                return a[max(0, cy - r):cy + r + 1, max(0, cx - r):cx + r + 1]
            foot = win_(lum0, bx, by, rf); ring = win_(lum0, bx, by, 3 * rf)
            foot_bright = float(foot.max() - np.median(ring)) if foot.size and ring.size else 0.0
            tm = win_(dark, tx, ty, rt).copy(); own = win_(lab_al, tx, ty, rt) > 0
            tip_mass = float((tm & ~ndimage.binary_dilation(own, iterations=2)).sum()) * gsd * gsd if tm.size else 0.0
            tex = float(win_(lum0, bx, by, int(1.5 / gsd)).std()) if foot.size else 0.0
            nrm = np.array([-u[1], u[0]]); tt = np.linspace(0.15, 0.85, 12)[:, None] * (tip - base)[None] + base[None]; hits = []
            for off in (-0.9, -0.55, 0.55, 0.9):
                q = np.round(tt + nrm[None] * off / gsd).astype(int); okq = (q[:, 0] >= 0) & (q[:, 0] < W) & (q[:, 1] >= 0) & (q[:, 1] < H)
                hits.append(dark[q[okq, 1], q[okq, 0]])
            clutter = float(np.concatenate(hits).mean()) if hits and sum(len(h_) for h_ in hits) else 0.0
            r = {'base_px': base, 'tip_px': tip, 'shadow_m': Lm, 'width_m': float(m['W']), 'bearing': float(math.degrees(math.atan2(u[0], -u[1])) % 360.0),
                 'foot_bright': foot_bright, 'tip_mass_m2': tip_mass, 'clutter': clutter, 'tex_base': tex, 'on_road': bool(road_in[np.clip(by, 0, H - 1), np.clip(bx, 0, W - 1)]),
                 'on_vehicle': bool(cov[np.clip(by, 0, H - 1), np.clip(bx, 0, W - 1)]), 'edge': edge, 'arms': []}
            for a in arms:
                for end, far in ((a['ends'][0], a['ends'][1]), (a['ends'][1], a['ends'][0])):
                    w = (end - base) * gsd; t = float(w @ u); d = abs(float(w @ np.array([u[1], -u[0]])))
                    if -0.4 <= t <= Lm + 0.5 and d <= P['ARM_JOIN']:
                        fv = (far - end) * gsd
                        r['arms'].append({'join_along_shadow_m': max(t, 0.0), 'length_m': float(np.hypot(*fv)), 'bearing_deg': float(math.degrees(math.atan2(fv[0], -fv[1])) % 360.0), 'width_m': float(a['W'])}); break
            E, N = ortho.px_to_en(np.array([base[0], tip[0]]), np.array([base[1], tip[1]])); r['base_en'] = np.array([E[0], N[0]]); r['tip_en'] = np.array([E[1], N[1]])
            rows.append(r)
        # where this year could not have shown a post: building shadow, on a 1 m grid
        f = 13; h2, w2 = H // f, W // f; ys, xs = np.mgrid[0:h2, 0:w2]; E, N = ortho.px_to_en((xs.ravel() * f + f / 2).astype(float), (ys.ravel() * f + f / 2).astype(float))
        shf = bsh[:h2 * f, :w2 * f].reshape(h2, f, w2, f).mean((1, 3)).ravel()
        out['years'][y] = {'sun_from_known_posts_deg': cal, 'sun_shadow_bearing_deg': round(sun, 2), 'bearing_votes_m': round(votes, 1), 'strokes': rows, 'E': E.astype(np.float32), 'N': N.astype(np.float32), 'shadow': shf.astype(np.float32)}
    out['seconds'] = round(time.time() - t0, 1)
    os.makedirs(os.path.join(cache, 'posts'), exist_ok=True); pickle.dump(out, open(os.path.join(cache, 'posts', tid + '.pkl'), 'wb'))
    return tid, {y: (len(v['strokes']), v['sun_shadow_bearing_deg'], v['bearing_votes_m']) for y, v in out['years'].items()}, out['seconds']


def one(a):
    return run(*a)


def calib(a):
    """first half of the second pass: only the bearings from known posts, per tile and year"""
    tid, cache, known = a; out = {}
    for y in YEARS:
        img = os.path.join(cache, 'img', str(y), tid + '.png'); mk = os.path.join(cache, 'masks', f'{tid}_{y}.npz')
        if not os.path.exists(img) or not os.path.exists(mk):
            continue
        ortho = Ortho.load(img, origin=lapgeo.ORIGIN); gsd = float(np.mean(ortho.gsd)); bsh = unpack(np.load(mk), 'shadow')
        lum = ndimage.gaussian_filter(ortho.rgb.mean(-1), 0.6); k = max(3, int(round(P['HAT_M'] / gsd)) | 1)
        bg = cv2.morphologyEx(lum.astype(np.float32), cv2.MORPH_CLOSE, np.ones((k, k), np.uint8)); bh = bg - lum
        dark = (bh >= np.maximum(P['DARK_MIN'], P['DARK_REL'] * bg)) & (bg >= P['BG_MIN']) & ~ndimage.binary_dilation(bsh, iterations=int(P['SHADOW_PAD_M'] / gsd))
        out[y] = sun_from_posts(dark, ortho, gsd, known)
    return tid, out


if __name__ == '__main__':
    import json, multiprocessing as mp
    cache = sys.argv[1]; args = sys.argv[2:]; known = None
    if '--known' in args:                       # second pass: <file> = [[E, N], ...] of posts the eye confirmed at a shadow's foot
        known = json.load(open(args[args.index('--known') + 1])); args = args[:args.index('--known')]
    ids = args or [t['id'] for t in lapgeo.tiles()]; T = {t['id']: t for t in lapgeo.tiles()}
    def inside(t):
        b = T[t]['box']; return [k for k in known if b[0] + 4 <= k[0] <= b[2] - 4 and b[1] + 4 <= k[1] <= b[3] - 4]
    jobs = [(t, cache) for t in ids]
    if known is not None:
        with mp.Pool(3) as pool:
            cal = dict(pool.map(calib, [(t, cache, inside(t)) for t in ids]))
        # a calibration is kept only with SUN_KNOWN_GOOD votes and within SUN_PLAUSIBLE_DEG of a bearing seen by eye for that
        # year (2022 and 2018 north; 2020 north-west or north: two flight lines); a tile without one takes the nearest kept
        # tile's bearing in that year (its own when kept: distance 0)
        PLAUS = {2022: (0.0,), 2018: (0.0,), 2020: (305.0, 0.0)}
        def good(y, c):
            return c is not None and c[0] is not None and c[1] >= P['SUN_KNOWN_GOOD'] and min(abs((c[0] - p + 180) % 360 - 180) for p in PLAUS[y]) <= P['SUN_PLAUSIBLE_DEG']
        fb = {}
        for t in ids:
            fb[t] = {}
            for y in YEARS:
                have = [(math.hypot(T[t]['cell'][0] - T[u]['cell'][0], T[t]['cell'][1] - T[u]['cell'][1]), cal[u][y][0]) for u in ids if good(y, cal[u].get(y))]
                if have:
                    fb[t][y] = min(have)[1]
        json.dump({'_doc': 'shadow bearing (compass, foot -> tip) per work tile and flight year from the first pass\'s eye-confirmed posts: [bearing or null, posts voting]; used = the bearing the second pass read with (vetted, or the nearest vetted tile\'s)', 'tiles': {t: {str(y): v for y, v in c.items()} for t, c in cal.items()}, 'used': {t: {str(y): v for y, v in f.items()} for t, f in fb.items()}},
                  open(os.path.join(cache, 'posts_sun.json'), 'w'), indent=1)
        jobs = [(t, cache, [], fb[t]) for t in ids]          # [] known: run() takes the vetted bearing, not its own vote
    with mp.Pool(3) as pool:
        for r in pool.imap_unordered(one, jobs):
            print(r, flush=True)

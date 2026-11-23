"""Posts, masts and their arms read off an orthophoto by their shadows (PLAN section 4b: lamps, signals, sign posts).

    python3 strokes_read.py <image.png> <out.json> [--overlay out.jpg] [--lidar pts.npz]

Why shadows: the lidar holds no returns on poles here (4 returns per m2; measured on the pilot), and in a near-nadir
3-inch aerial a post is a dot. Its shadow is a thin dark stroke of one bearing (the sun's) starting AT THE POST'S BASE,
as long as the post is tall. So: the base is the sun-ward end of the stroke, the height is its length times
tan(sun elevation), and an arm is a second stroke that leaves the first part-way along it.

Method (thresholds [invented], written into the output):
  dark     the luminance bottom-hat over HAT_M at least DARK under a background brighter than BG_MIN (sunlit ground);
  bearing  thin straight dark strokes vote; the sun's bearing is the peak of their lengths away from the street grid's
           own directions (kerbs and joints run with the streets), refined to the weighted mean within 3 degrees;
  posts    the dark mask opened with a line LINE_M long on that bearing keeps only strokes running that way; each at
           least POST_L_MIN long and no wider than POST_W_MAX is a post's shadow; base = its sun-ward end;
  arms     the rest of the dark mask opened with lines on other bearings: a stroke at least ARM_L_MIN long that starts
           within ARM_JOIN of a post's shadow is that post's arm (length, bearing, height of the join);
  height   shadow length x tan(elevation). The elevation is fitted from posts that DO have a lidar return on top
           (--lidar), else left unknown and heights are not written.
Not read: what a post carries (lamp, signal head, sign), posts in shade, posts whose shadow falls on a vehicle, a
wall or a tree's shadow. Trunks, people, bollards and fence posts cast the same strokes: a stroke is a candidate.
"""
import json, math, os, sys
import numpy as np
from scipy import ndimage
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paint_read as pr  # noqa: E402
from scripts.aerial.engine.ortho import Ortho  # noqa: E402

P = {'HAT_M': 1.6, 'DARK': 28.0, 'BG_MIN': 90.0, 'LINE_M': 1.1, 'POST_L_MIN': 1.3, 'POST_W_MAX': 0.75, 'ARM_L_MIN': 2.0, 'ARM_W_MAX': 0.9,
     'ARM_JOIN': 1.0, 'GRID_AVOID_DEG': 1.2, 'TOP_R': 0.9}


def line_fp(length_px, bearing_deg):
    n = int(length_px) | 1; fp = np.zeros((n, n), bool); c = n // 2; a = math.radians(bearing_deg)
    for t in np.linspace(-c, c, 4 * n):
        fp[int(round(c - t * math.cos(a))), int(round(c + t * math.sin(a)))] = True
    return fp


def strokes(mask, gsd, lmin, wmax):
    lab, n = ndimage.label(mask, structure=np.ones((3, 3))); out = []
    for i, sl in enumerate(ndimage.find_objects(lab), 1):
        if max(sl[0].stop - sl[0].start, sl[1].stop - sl[1].start) * gsd < lmin * 0.7:
            continue
        ys, xs = np.nonzero(lab[sl] == i); ys = ys + sl[0].start; xs = xs + sl[1].start
        m = pr.measure(ys, xs, gsd)
        if m is not None and m['W'] <= wmax and m['L'] >= lmin:
            out.append(m)
    return out


def read(image, lidar=None):
    ortho = Ortho.load(image, origin=pr.ORIGIN); gsd = float(np.mean(ortho.gsd))
    lum = ndimage.gaussian_filter(ortho.rgb.mean(-1), 0.6); k = max(3, int(round(P['HAT_M'] / gsd)) | 1)
    bg = ndimage.grey_closing(lum, size=(k, k)); bh = bg - lum
    dark = (bh >= P['DARK']) & (bg >= P['BG_MIN'])
    # the sun's bearing: thin strokes vote by length, away from 0 / 90 (the street grid here; the image is north-up within a degree)
    thin = strokes(ndimage.binary_opening(dark, iterations=1), gsd, 1.5, 0.45)
    b = np.array([m['bearing'] for m in thin]); L = np.array([m['L'] for m in thin])
    off = np.minimum.reduce([np.abs(b - g) for g in (0, 90, 180)]) > P['GRID_AVOID_DEG']
    hist, edges = np.histogram(b[off], bins=180, range=(0, 180), weights=L[off]); pk = int(np.argmax(ndimage.uniform_filter1d(hist, 3, mode='wrap')))
    near = off & (np.abs((b - (pk + 0.5) + 90) % 180 - 90) < 3)
    sun_b = float(np.average(b[near], weights=L[near])); votes = int(near.sum())
    fp = line_fp(P['LINE_M'] / gsd, sun_b)
    along = ndimage.binary_opening(dark, structure=fp)
    posts = strokes(along, gsd, P['POST_L_MIN'], P['POST_W_MAX'])
    rest = dark & ~ndimage.binary_dilation(along, iterations=1)
    arms = []
    for ab in range(0, 180, 10):
        if abs((ab - sun_b + 90) % 180 - 90) < 12:
            continue
        for m in strokes(ndimage.binary_opening(rest, structure=line_fp(1.6 / gsd, ab)), gsd, P['ARM_L_MIN'], P['ARM_W_MAX']):
            if abs((m['bearing'] - ab + 90) % 180 - 90) <= 6:
                arms.append(m)
    # sun-ward end = the base. The sun is in the south: the shadow runs to the north side, so the base is the end with the larger y (image y is south)
    out = []
    for m in posts:
        e0, e1 = m['ends']; base, tip = (e0, e1) if e0[1] > e1[1] else (e1, e0)
        v = (tip - base) * gsd; Ls = float(np.hypot(*v)); u = v / Ls
        p = {'base_px': base, 'tip_px': tip, 'shadow_m': Ls, 'width_m': m['W'], 'bearing': m['bearing'], 'arms': []}
        for a in arms:
            for end, far in ((a['ends'][0], a['ends'][1]), (a['ends'][1], a['ends'][0])):
                w = (end - base) * gsd; t = float(w @ u); d = abs(float(w @ np.array([u[1], -u[0]])))
                if -0.3 <= t <= Ls + 0.5 and d <= P['ARM_JOIN']:
                    fv = (far - end) * gsd
                    p['arms'].append({'join_along_shadow_m': max(t, 0.0), 'length_m': float(np.hypot(*fv)),
                                      'bearing_deg': (math.degrees(math.atan2(fv[0], -fv[1])) % 360), 'width_m': a['W']}); break
        out.append(p)
    tan_el = None; fit = None
    if lidar is not None:
        Lz = np.load(lidar); e, n = ortho.lonlat_to_en(Lz['lon'], Lz['lat']); z = Lz['z']; cls = Lz['cls']; hs = []
        for p in out:
            E, N = ortho.px_to_en(p['base_px'][0], p['base_px'][1]); d = np.hypot(e - E, n - N)
            g = z[(d < 4) & (cls == 2)]; t = z[(d < P['TOP_R']) & (cls == 1)]
            if len(g) and len(t) and t.max() - np.median(g) > 2.0:
                p['lidar_top_m'] = float(t.max() - np.median(g)); hs.append((p['shadow_m'], p['lidar_top_m']))
        if len(hs) >= 3:
            r = np.array([h / s for s, h in hs]); med = float(np.median(r)); keep = np.abs(r - med) < 0.25 * med
            if keep.sum() >= 3:
                tan_el = float(np.median(r[keep])); fit = {'posts_with_a_lidar_top': len(hs), 'used': int(keep.sum()),
                                                            'tan_elevation': round(tan_el, 3), 'elevation_deg': round(math.degrees(math.atan(tan_el)), 1),
                                                            'ratio_spread_p16_p84': [round(float(v), 3) for v in np.percentile(r[keep], [16, 84])]}
    return ortho, gsd, out, {'sun_shadow_bearing_deg': round(sun_b, 2), 'bearing_votes': votes, 'sun_fit': fit}, tan_el


def emit(ortho, posts, meta, tan_el, image):
    rows = []
    for k, p in enumerate(posts):
        lon, lat = ortho.px_to_lonlat(np.array([p['base_px'][0]]), np.array([p['base_px'][1]]))
        r = {'id': f's{k:04d}', 'base_lonlat': [round(float(lon[0]), 7), round(float(lat[0]), 7)], 'base_px': [round(float(v), 1) for v in p['base_px']],
             'shadow_m': round(p['shadow_m'], 2), 'shadow_width_m': round(p['width_m'], 2)}
        if tan_el:
            r['height_m'] = round(p['shadow_m'] * tan_el, 1)
        if 'lidar_top_m' in p:
            r['lidar_top_m'] = round(p['lidar_top_m'], 1)
        r['arms'] = [{'length_m': round(a['length_m'], 1), 'bearing_deg': round(a['bearing_deg'], 1),
                      **({'height_m': round(a['join_along_shadow_m'] * tan_el, 1)} if tan_el else {'join_along_shadow_m': round(a['join_along_shadow_m'], 2)})} for a in p['arms']]
        rows.append(r)
    return {'_doc': 'Post candidates read from their shadows by strokes_read.py. base = the sun-ward end of the shadow. A candidate is a thin '
                    'upright thing that casts a shadow: what it is has not been read here.', 'image': os.path.basename(image),
            'georeference': ortho.describe(), 'thresholds_invented': P, **meta, 'candidates': rows}


if __name__ == '__main__':
    a = sys.argv
    lid = a[a.index('--lidar') + 1] if '--lidar' in a else None
    ortho, gsd, posts, meta, tan_el = read(a[1], lid)
    res = emit(ortho, posts, meta, tan_el, a[1]); json.dump(res, open(a[2], 'w'), indent=1)
    print(len(posts), 'post candidates;', sum(1 for p in posts if p['arms']), 'with an arm;', meta)
    if '--overlay' in a:
        im = Image.fromarray(ortho.rgb.astype(np.uint8)); d = ImageDraw.Draw(im)
        for r, p in zip(res['candidates'], posts):
            (x0, y0), (x1, y1) = p['base_px'], p['tip_px']
            d.line([x0, y0, x1, y1], fill=(255, 0, 0), width=2); d.ellipse([x0 - 6, y0 - 6, x0 + 6, y0 + 6], outline=(0, 255, 0), width=2)
            d.text((x0 + 9, y0 - 4), r['id'][1:].lstrip('0') or '0', fill=(255, 255, 0))
            for am in p['arms']:
                pass
        im.save(a[a.index('--overlay') + 1], quality=85)

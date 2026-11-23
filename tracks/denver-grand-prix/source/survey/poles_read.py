"""Pole candidates from the lidar (PLAN section 4b, lamps and signal masts): thin vertical clusters standing alone.

    python3 poles_read.py <image.png> <lidar.npz> <out.json> [--overlay out.jpg]

The image is only the frame (its georeference, through the aerial engine's Ortho) and the picture the candidates are
drawn on for the check by eye; the candidates come from the points alone.

Method (every number [invented] tuning, written into the output):
  ground   the lowest class-2 return per 1 m cell, gaps filled from the nearest cell; h = z - ground;
  shaft    returns that are not ground, bridge deck or noise, with h in SHAFT (above vehicles and people, below most
           arms and crowns), binned at CELL_M; a candidate is a connected group of occupied cells no wider than THIN_M
           holding at least MIN_PTS returns over at least MIN_SPAN m of height;
  alone    few other shaft returns between ALONE_R (a wall, a hedge, a trunk's low branches fail this);
  top      the highest return within TOP_R of the group's centre joined to it without a gap over GAP_M: the pole's height;
  crown    returns above CROWN_H within CROWN_R: a tree carries hundreds, a pole a few (its arm and head);
  arm      returns between ARM_H forming a straight run out of the pole at least ARM_MIN long: a mast arm's length and
           bearing. A lamp's short bracket and a signal's long arm are told apart by that length only.
What it cannot see: a post under a tree's crown (May 2020, leaf-on), a post against a wall, and at 3-4 returns per
square metre any post the scan happened not to hit twice. Those are counted by eye against the aerial, not here.
"""
import json, math, os, sys
import numpy as np
from scipy import ndimage
from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), *[os.pardir] * 4))
sys.path.insert(0, ROOT)
from scripts.aerial.engine.ortho import Ortho  # noqa: E402

ORIGIN = (-104.9849, 39.7401)
P = {'SHAFT': (2.3, 5.0), 'CELL_M': 0.4, 'THIN_M': 1.0, 'MIN_PTS': 3, 'MIN_SPAN': 1.2, 'ALONE_R': (1.0, 2.2), 'ALONE_MAX': 6,
     'TOP_R': 0.8, 'GAP_M': 1.6, 'CROWN_H': 3.5, 'CROWN_R': 3.0, 'CROWN_MAX': 120, 'ARM_H': (4.5, 12.0), 'ARM_MIN': 2.5, 'ARM_W': 0.5,
     'MIN_TOP': 3.0}


def read(image, npz):
    ortho = Ortho.load(image, origin=ORIGIN)
    L = np.load(npz); e, n = ortho.lonlat_to_en(L['lon'], L['lat']); z = L['z']; cls = L['cls']
    x0, y0 = e.min(), n.min(); W = int(e.max() - x0) + 2; H = int(n.max() - y0) + 2
    gi = (n - y0).astype(int); gj = (e - x0).astype(int)
    g = np.full((H, W), np.inf); m2 = cls == 2
    np.minimum.at(g, (gi[m2], gj[m2]), z[m2])
    miss = ~np.isfinite(g); idx = ndimage.distance_transform_edt(miss, return_distances=False, return_indices=True)
    g = g[idx[0], idx[1]]; g = ndimage.median_filter(g, 3)
    h = z - g[gi, gj]
    ok = ~np.isin(cls, (2, 7, 17, 18))
    sh = ok & (h >= P['SHAFT'][0]) & (h <= P['SHAFT'][1])
    c = P['CELL_M']; ci = ((n - y0) / c).astype(int); cj = ((e - x0) / c).astype(int)
    occ = np.zeros((int(H / c) + 2, int(W / c) + 2), np.int32); np.add.at(occ, (ci[sh], cj[sh]), 1)
    lab, k = ndimage.label(occ > 0, structure=np.ones((3, 3)))
    plab = np.where(sh, lab[ci, cj], 0)
    E_ = np.stack([e, n], 1); out = []
    order = np.argsort(plab, kind='stable'); bounds = np.searchsorted(plab[order], np.arange(1, k + 2))
    for i in range(1, k + 1):
        ids = order[bounds[i - 1]:bounds[i]]
        if len(ids) < P['MIN_PTS']:
            continue
        q = E_[ids]; ext = float(np.hypot(*(q.max(0) - q.min(0))))
        if ext > P['THIN_M'] or h[ids].max() - h[ids].min() < P['MIN_SPAN']:
            continue
        ctr = q.mean(0); d = np.hypot(e - ctr[0], n - ctr[1])
        alone = int((sh & (d > P['ALONE_R'][0]) & (d < P['ALONE_R'][1])).sum())
        if alone > P['ALONE_MAX']:
            continue
        col = ok & (d < P['TOP_R']) & (h > 0.5); hs = np.sort(h[col]); top = hs[0] if len(hs) else 0
        for v in hs:
            if v - top > P['GAP_M'] and top > P['SHAFT'][0]:
                break
            top = v
        if top < P['MIN_TOP']:
            continue
        crown = int((ok & (d < P['CROWN_R']) & (h > P['CROWN_H'])).sum())
        arm = None
        am = ok & (d < 14) & (d > 0.6) & (h >= P['ARM_H'][0]) & (h <= min(P['ARM_H'][1], top + 0.8))
        if am.sum() >= 4 and crown <= P['CROWN_MAX'] * 3:
            v = E_[am] - ctr; ang = np.degrees(np.arctan2(v[:, 0], v[:, 1])) % 360
            hist, _ = np.histogram(ang, bins=72, range=(0, 360)); b = int(np.argmax(hist + np.roll(hist, 1) + np.roll(hist, -1)))
            a0 = math.radians(b * 5 + 2.5); ux = np.array([math.sin(a0), math.cos(a0)])
            along = v @ ux; across = np.abs(v @ np.array([ux[1], -ux[0]])); on = (across < P['ARM_W']) & (along > 0)
            if on.sum() >= 4:
                s_ = np.sort(along[on]); reach = s_[0]
                for t in s_:
                    if t - reach > 1.5:
                        break
                    reach = t
                if reach >= P['ARM_MIN'] and s_[0] < 1.6:
                    arm = {'length_m': round(float(reach), 1), 'bearing_deg': round(b * 5 + 2.5, 1), 'height_m': round(float(np.median(h[am][on])), 1),
                           'returns': int((on & (along <= reach)).sum())}
        lon, lat = ortho.en_to_lonlat(ctr[0], ctr[1])
        out.append({'lonlat': [round(float(lon), 7), round(float(lat), 7)], 'en': ctr, 'height_m': round(float(top), 1), 'shaft_returns': int(len(ids)),
                    'returns_near': int(col.sum()), 'crown_returns_3m': crown, 'other_shaft_returns_1_2m': alone, 'arm': arm,
                    'ground_m': round(float(g[int(ctr[1] - y0), int(ctr[0] - x0)]), 2),
                    'lidar_class': ('tree_or_under_crown' if crown > P['CROWN_MAX'] else 'pole')})
    return ortho, out


def overlay(ortho, cands, path, extra=None):
    im = Image.fromarray(ortho.rgb.astype(np.uint8)); d = ImageDraw.Draw(im)
    for k, c in enumerate(cands):
        x, y = ortho.en_to_px(c['en'][0], c['en'][1]); x, y = float(x), float(y)
        col = (255, 60, 60) if c['lidar_class'] == 'pole' else (120, 255, 120)
        d.ellipse([x - 14, y - 14, x + 14, y + 14], outline=col, width=3)
        d.text((x + 16, y - 16), f"{k}:{c['height_m']:.0f}", fill=col)
        if c['arm']:
            a = math.radians(c['arm']['bearing_deg']); L = c['arm']['length_m']
            x2, y2 = ortho.en_to_px(c['en'][0] + math.sin(a) * L, c['en'][1] + math.cos(a) * L)
            d.line([x, y, float(x2), float(y2)], fill=(255, 200, 0), width=3)
    im.save(path, quality=82)


if __name__ == '__main__':
    a = sys.argv
    ortho, cands = read(a[1], a[2])
    if '--overlay' in a:
        overlay(ortho, cands, a[a.index('--overlay') + 1])
    for c in cands:
        c.pop('en')
    json.dump({'_doc': 'Pole candidates from CO_DRCOG_2_2020 lidar by poles_read.py. Not yet checked against the aerial.', 'thresholds_invented': P,
               'candidates': cands}, open(a[3], 'w'), indent=1)
    print(len(cands), 'candidates;', sum(1 for c in cands if c['lidar_class'] == 'pole'), 'pole-like;', sum(1 for c in cands if c['arm']), 'with an arm')

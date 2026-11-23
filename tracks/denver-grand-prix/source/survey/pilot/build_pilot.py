"""The survey pilot (PLAN 4b): Colfax from Logan to Lincoln. Runs the readers on the pilot box and writes this folder.

    python3 tracks/denver-grand-prix/source/survey/pilot/build_pilot.py <cache-dir>

<cache-dir> holds what stays out of git: pilot_2022.png + .json (drapp_mosaic.py 2022 -135 -34 250 38, tile S1E100b),
pilot_lidar.npz (ept_box.py over the same box) ; both are fetched here if missing. Writes paint.json, poles.json,
signs.json and stills/*.jpg beside this file. PILOT.md is written by hand from their numbers.
"""
import json, math, os, subprocess, sys, collections
import numpy as np
from scipy import ndimage
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__)); S = os.path.dirname(HERE); ROOT = os.path.abspath(os.path.join(S, *[os.pardir] * 4))
sys.path.insert(0, ROOT); sys.path.insert(0, S)
import paint_read as pr, strokes_read as sr  # noqa: E402

BOX = (-135, -34, 250, 38)


def main(cache):
    img = os.path.join(cache, 'pilot_2022.png'); lid = os.path.join(cache, 'pilot_lidar.npz')
    if not os.path.exists(img):
        subprocess.check_call([sys.executable, os.path.join(S, 'drapp_mosaic.py'), '2022', *map(str, BOX), img, '--tiles', 'S1E100b,S1E100a,N1E190d,N1E190c'])
    if not os.path.exists(lid):
        subprocess.check_call([sys.executable, os.path.join(S, 'ept_box.py'), '-104.98655', '39.73974', '-104.98190', '39.74050', os.path.join(cache, 'ept'), lid])
    # ---- paint
    ortho, gsd, marks, stats, masks = pr.read(img, lid); items, left = pr.group(marks, gsd)
    res = pr.emit(ortho, gsd, marks, items, left, stats, img)
    for it in res['items']:
        weak = it['class'] == 'symbol' or it.get('pattern') == 'single dash or fragment' or (it['class'] == 'bar' and it['length_m'] < 1.5)
        it['grade'] = 'detected' if weak else 'measured'
    conf = collections.Counter(); 
    for it in res['items']:
        conf[(it['grade'], str(it.get('lidar_confirms')))] += 1
    res['grades'] = {g: sum(1 for it in res['items'] if it['grade'] == g) for g in ('measured', 'detected')}
    res['lidar_check_by_grade'] = {f'{g} / lidar {c}': n for (g, c), n in sorted(conf.items())}
    res['stats'] = {k: (float(v) if isinstance(v, np.floating) else v) for k, v in stats.items()}
    res['source_image'] = json.load(open(os.path.splitext(img)[0] + '.json'))
    json.dump(res, open(os.path.join(HERE, 'paint.json'), 'w'), indent=1)
    pr.overlay(ortho, marks, items, left, os.path.join(cache, 'pilot_paint_overlay.jpg'), masks=masks)
    win = masks[2]
    # ---- posts from shadows
    o2, _, posts, meta, _ = sr.read(img, None)
    cands = sr.emit(o2, posts, meta, None, img)['candidates']
    road_in = ndimage.binary_erosion(win, iterations=int(0.5 / gsd)); near = pr.window(ortho, pr.osm_lines(ortho), gsd)
    B = np.array([c['base_px'] for c in cands]); kept = []; why = collections.Counter()
    for i, c in enumerate(cands):
        x, y = int(round(c['base_px'][0])), int(round(c['base_px'][1]))
        if not (0 <= x < ortho.W and 0 <= y < ortho.H) or not near[y, x]:
            why['outside the corridor'] += 1; continue
        if road_in[y, x]:
            why['on the roadway (a vehicle, a mark)'] += 1; continue
        if int((np.hypot(*(B - B[i]).T) * gsd < 2.0).sum()) - 1 > 2:
            why['in a cluster of strokes (a tree, a fence)'] += 1; continue
        if c['shadow_m'] < 1.6:
            why['shadow under 1.6 m (a bollard, a person)'] += 1; continue
        kept.append(c)
    census = json.load(open(os.path.join(HERE, 'census_by_eye.json')))
    real = {p['candidate']: p for p in census['posts'] if p['candidate'] is not None}
    for k, c in enumerate(kept):
        c['k'] = k; c['grade'] = 'detected'; c['what'] = 'a thin upright thing that casts a shadow: unread'
        if k in real:
            c['grade'] = 'measured'; c['class'] = real[k]['class']; c['what'] = real[k]['what'] + ' (class read by eye)'
        elif k in census['reader_false_candidates_in_window']:
            c['grade'] = 'rejected by eye'; c['what'] = 'not a post (a trunk, a fence, a kerb edge)'
    byeye = []
    for p in census['posts']:
        if p['candidate'] is None:
            lon, lat = ortho.px_to_lonlat(np.array([p['px'][0]]), np.array([p['px'][1]]))
            byeye.append({'grade': 'measured', 'read': 'by eye off the aerial, about +-0.5 m, no second source', 'class': p['class'], 'what': p['what'],
                          'base_lonlat': [round(float(lon[0]), 7), round(float(lat[0]), 7)], 'base_px': p['px'],
                          **{k_: v for k_, v in p.items() if k_.startswith('arm_')}})
    n_real = len(census['posts']); n_found = len(real); n_false = len(census['reader_false_candidates_in_window'])
    json.dump({'_doc': 'Posts on the pilot stretch (lamps, signal masts, sign posts are not told apart from the air). candidates: the shadow '
                       'reader (strokes_read.py), filtered to the corridor and off the roadway; base = the sun-ward end of the shadow. by_eye: '
                       'posts the reader missed at the one junction read by eye (census_by_eye.json). Heights are NOT written: the sun\'s '
                       'elevation at the flight is not known (see PILOT.md).', 'image': 'pilot_2022.png (DRCOG 2022, 3-inch)', **meta,
               'reader_dropped': dict(why), 'candidates_kept': len(kept),
               'sherman_junction_check': {'posts_by_eye': n_real, 'found_by_the_reader': n_found, 'recall': round(n_found / n_real, 2),
                                          'reader_candidates_in_window': n_found + n_false + len(census['reader_duplicate_in_window']),
                                          'not_posts': n_false, 'precision': round(n_found / (n_found + n_false), 2),
                                          'signal_masts_by_eye': 3, 'signal_masts_found': 1},
               'candidates': kept, 'by_eye': byeye}, open(os.path.join(HERE, 'poles.json'), 'w'), indent=1)
    # ---- signs: only what OSM implies, per junction; nothing placed
    o = json.load(open(os.path.join(ROOT, 'tracks', 'denver-grand-prix', 'source', 'osm.json')))
    J = {'Lincoln': {'cross': 'North Lincoln Street'}, 'Sherman': {'cross': 'Sherman Street'}, 'Grant': {'cross': 'Grant Street'}, 'Logan': {'cross': 'Logan Street'}}
    for w in o['ways']:
        t = w['tags']
        for j in J.values():
            if t.get('name') == j['cross'] and t.get('highway') not in (None, 'service', 'footway'):
                j.setdefault('oneway', set()).add(t.get('oneway', 'not tagged')); j.setdefault('maxspeed', set()).add(t.get('maxspeed', 'not tagged'))
                j.setdefault('turn_lanes', set()).add(t.get('turn:lanes', 'not tagged'))
    signs = []
    for name, j in J.items():
        signs.append({'junction': f'Colfax / {name}', 'grade': 'tagged', 'position': 'none claimed beyond the junction',
                      'control': 'traffic signals (OSM highway=traffic_signals on both Colfax carriageways)',
                      'implied_by_osm': {'cross_street_oneway': sorted(j.get('oneway', [])), 'cross_street_maxspeed': sorted(j.get('maxspeed', [])),
                                         'cross_street_turn_lanes': sorted(j.get('turn_lanes', [])), 'colfax_maxspeed': '30 mph',
                                         'colfax_bus_lanes': 'designated|yes (OSM today; NOT in the 2022 or 2023 imagery: see PILOT.md)'},
                      'faces': 'not read: no source from the air. Street-level imagery (Mapillary, E3) or Kevin\'s captures would give the posts and the faces.'})
    json.dump({'_doc': 'Signs on the pilot stretch: only what OSM implies per junction (grade tagged, no post position, no face). Candidate posts '
                       'are in poles.json (a sign post and a lamp post are not told apart from the air).', 'junctions': signs},
              open(os.path.join(HERE, 'signs.json'), 'w'), indent=1)
    # ---- stills
    ov = Image.open(os.path.join(cache, 'pilot_paint_overlay.jpg'))
    ov.crop((1500, 290, 2140, 870)).resize((1100, 997), Image.LANCZOS).save(os.path.join(HERE, 'stills', 'paint_sherman.jpg'), quality=72)
    ov.crop((2950, 330, 3760, 830)).resize((1100, 679), Image.LANCZOS).save(os.path.join(HERE, 'stills', 'paint_grant.jpg'), quality=72)
    im = Image.open(img).crop((1500, 290, 2140, 870)).resize((1100, 997), Image.LANCZOS); d = ImageDraw.Draw(im); z = 1100 / 640
    for c in kept:
        x, y = c['base_px']
        if 1500 <= x < 2140 and 290 <= y < 870:
            col = {'measured': (0, 255, 0), 'detected': (255, 220, 0), 'rejected by eye': (255, 60, 60)}[c['grade']]
            X, Y = (x - 1500) * z, (y - 290) * z; d.ellipse([X - 10, Y - 10, X + 10, Y + 10], outline=col, width=3)
    for p in byeye:
        X, Y = (p['base_px'][0] - 1500) * z, (p['base_px'][1] - 290) * z; d.rectangle([X - 10, Y - 10, X + 10, Y + 10], outline=(0, 200, 255), width=3)
    im.save(os.path.join(HERE, 'stills', 'posts_sherman.jpg'), quality=72)
    print('paint', res['counts'], res['grades'], res['lidar_check_by_grade']); print('posts kept', len(kept), dict(why), 'by eye added', len(byeye))


if __name__ == '__main__':
    main(sys.argv[1])

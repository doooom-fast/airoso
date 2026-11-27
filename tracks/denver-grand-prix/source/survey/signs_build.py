"""signs.json for the lap: what OSM implies at each junction, grade 'tagged'. No post position, no face (PLAN 4b).

    python3 signs_build.py            # writes signs.json beside this file from source/osm.json

Per junction (lapgeo.junctions(): the lap's way nodes where another street meets it, the two carriageways of one crossing
merged): the control OSM tags (signals, a stop node on an approach, or nothing tagged), the lap street's and each cross
street's one-way, limit, lanes, turn lanes and bus / bike lane tags, the rail crossings, and the signs those tags IMPLY
under the MUTCD (a one-way cross street implies ONE WAY plates and a turn prohibition against it; a tagged limit implies a
speed limit sign somewhere on the block; a stop node implies a STOP sign on that approach). 'Implied' is a rule applied to
a tag: not one sign here was seen. Each junction lists what a street-level source would have to supply.
Speed limit changes along the lap are listed once, where the tag changes from one lap way to the next.
"""
import json, math, os, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import lapgeo  # noqa: E402

NEED = ['the post of every sign (position to about a metre, which corner, on its own post or on a signal mast / lamp post)',
        'each face: the MUTCD code or the legend, its size, which way it faces',
        'street-name blades (overhead on the mast arm or on a corner post) and their text',
        'turn restrictions and lane-use signs at the stop line (R3 series): OSM holds turn:lanes for some approaches only, and no restriction relations are in the extract',
        'parking, bus-stop and loading signs along the kerb']


def main():
    o = lapgeo.osm(); L = lapgeo.lap(); W = {w['id']: w for w in o['ways']}
    legw = json.load(open(os.path.join(lapgeo.T, 'data', 'lap_ways.plan.json')))['legs']; lapways = [w for g in legw for w in g['ways']]
    stops = [(n, t) for n, t in o['node_tags'].items() if t.get('highway') in ('stop', 'give_way')]
    sE, sN = lapgeo.en([o['nodes'][n][0] for n, _ in stops], [o['nodes'][n][1] for n, _ in stops])
    byn = {}
    for w in o['ways']:
        for n in w['nodes']:
            byn.setdefault(n, []).append(w['id'])
    out = []
    for g in lapgeo.junctions():
        E = float(np.mean([r['E'] for r in g])); N = float(np.mean([r['N'] for r in g])); lon, lat = lapgeo.lonlat(E, N)
        sig = [r['node'] for r in g if r['signal_tag']]; cross_ids = sorted({w for r in g for w in r['cross_ways']})
        lap_ids = sorted({w for r in g for w in byn.get(r['node'], []) if w in lapways})
        def tags(wid, keys=('name', 'oneway', 'maxspeed', 'lanes', 'turn:lanes', 'bus:lanes', 'access:lanes', 'cycleway:left', 'cycleway:right', 'cycleway', 'highway')):
            t = W[wid]['tags']; return {'osm_way': wid, **{k: t[k] for k in keys if k in t}}
        near_stop = []
        for k, (n, t) in enumerate(stops):
            if math.hypot(sE[k] - E, sN[k] - N) <= 35 and any(w in cross_ids or w in lap_ids for w in byn.get(int(n), [])):
                near_stop.append({'osm_node': int(n), 'tag': t.get('highway'), 'direction': t.get('direction', 'not tagged'), 'on': sorted({W[w]['tags'].get('name', 'unnamed') for w in byn.get(int(n), [])})})
        rail = [r['node'] for r in g if r['node_tags'].get('railway') == 'level_crossing']
        control = 'traffic signals' if sig else ('stop / give-way on an approach' if near_stop else 'none tagged')
        implied = []
        if sig:
            implied.append({'what': 'signal faces for every approach', 'basis': f'highway=traffic_signals on {len(sig)} node(s)', 'see': 'signals.json for the masts read off the aerial'})
        for s_ in near_stop:
            implied.append({'what': 'STOP (R1-1)' if s_['tag'] == 'stop' else 'YIELD (R1-2)', 'on': s_['on'], 'basis': f"highway={s_['tag']} node {s_['osm_node']}"})
        for wid in cross_ids:
            t = W[wid]['tags']
            if t.get('oneway') == 'yes' and t.get('highway') != 'service':
                implied.append({'what': 'ONE WAY (R6-1 / R6-2) facing the lap\'s approach, and no turn against it (R3-1 / R3-2) or DO NOT ENTER (R5-1) at its exit end',
                                'on': t.get('name', 'unnamed'), 'basis': f'oneway=yes on way {wid}'})
        for r in rail:
            implied.append({'what': 'rail crossing at grade (light rail in the street): crossing signs / signals', 'basis': f'railway=level_crossing node {r}'})
        out.append({'junction': ' / '.join(sorted({n for r in g for n in r['lap_street']}) + sorted({n for r in g for n in r['cross'] if n not in r['lap_street']})),
                    's_m': [round(r['s'], 1) for r in sorted(g, key=lambda r: r['s'])], 'leg': sorted({L['legs'][int(lapgeo.where([r['E']], [r['N']])[2][0])] for r in g}),
                    'centre_lonlat': [round(float(lon), 7), round(float(lat), 7)], 'osm_nodes': [r['node'] for r in g], 'grade': 'tagged',
                    'position': 'none claimed beyond the junction', 'control': control, 'signal_nodes': sig, 'stop_nodes': near_stop, 'rail_crossing_nodes': rail,
                    'lap_street': [tags(w) for w in lap_ids], 'cross_streets': [tags(w) for w in cross_ids], 'implied_by_osm': implied, 'faces': 'not read: no source from the air',
                    'street_level_source_must_supply': NEED + (['whether the tagged signal is a full signal or a pedestrian / rail signal'] if sig else ['whether the junction is really uncontrolled, or the stop sign is simply not mapped'])})
    out.sort(key=lambda j: j['s_m'][0])
    # speed limits and lane rules along the lap, where the tag changes
    changes = []; last = {}
    nodes = json.load(open(os.path.join(lapgeo.T, 'data', 'lap_line.plan.json')))['nodes']; seenw = []
    for n, sn in zip(nodes, L['node_s']):
        if n['way'] in seenw:
            continue
        seenw.append(n['way']); t = W[n['way']]['tags']
        for k in ('maxspeed', 'bus:lanes', 'lanes', 'oneway'):
            v = t.get(k, 'not tagged')
            if last.get(k) != v:
                changes.append({'s_m': round(float(sn), 1), 'leg': n['leg'], 'street': t.get('name'), 'tag': k, 'value': v, 'osm_way': n['way'], 'was': last.get(k)}); last[k] = v
    speed = [c for c in changes if c['tag'] == 'maxspeed']
    rails = []
    for wid in lapways:
        for n in W[wid]['nodes']:
            if o['node_tags'].get(str(n), {}).get('railway') == 'level_crossing' and n not in [r['osm_node'] for r in rails]:
                lon, lat = o['nodes'][str(n)]; E, N = lapgeo.en(lon, lat); sn, dn, lg = lapgeo.where([E], [N])
                rails.append({'osm_node': n, 's_m': round(float(sn[0]), 1), 'off_lap_m': round(float(dn[0]), 1), 'leg': L['legs'][int(lg[0])], 'street': W[wid]['tags'].get('name'), 'lonlat': [lon, lat], 'grade': 'tagged',
                              'implies': 'light rail crosses the street at grade: crossing signs and signals; none seen', 'tags': o['node_tags'][str(n)]})
    rails.sort(key=lambda r: r['s_m'])
    doc = {'_doc': 'Signs on the Denver Grand Prix lap: ONLY what OSM implies per junction (grade tagged). No sign was seen; no post position and no face '
                   'is claimed. Posts that may carry signs are in lamps.json / signals.json (a sign post and a lamp post are not told apart from the air '
                   'unless the eye could). Written by signs_build.py from source/osm.json.',
           'osm_as_of': o.get('osm_base'), 'written_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'grade_shares': {'tagged': 1.0, 'measured': 0.0, 'detected': 0.0},
           'counts': {'junctions': len(out), 'with_signals': sum(1 for j in out if j['signal_nodes']), 'signal_nodes': sum(len(j['signal_nodes']) for j in out),
                      'with_a_stop_or_yield_node': sum(1 for j in out if j['stop_nodes']), 'nothing_tagged': sum(1 for j in out if j['control'] == 'none tagged'),
                      'rail_crossings_at_grade': len(rails), 'one_way_cross_streets': sum(1 for j in out for i in j['implied_by_osm'] if i['what'].startswith('ONE WAY'))},
           'speed_limit_along_the_lap': [{'from_s_m': c['s_m'], 'street': c['street'], 'maxspeed': c['value'], 'implies': 'a speed limit sign (R2-1) on this block if the limit is posted; none seen', 'osm_way': c['osm_way']} for c in speed],
           'rail_crossings_at_grade': rails,
           'bus_lane_tags_along_the_lap': [c for c in changes if c['tag'] == 'bus:lanes'],
           'colfax_note': 'OSM today tags Colfax two lanes each way with bus:lanes=designated (the bus rapid transit rebuild). The newest free pictures (2022, and NAIP 2023-09) show the '
                          'street before it. Bus-lane signs implied by those tags are therefore NOT in the surveyed state (PLAN D8); they are listed here as changed since, not surveyed.',
           'junctions': out}
    json.dump(doc, open(os.path.join(HERE, 'signs.json'), 'w'), indent=1); print(doc['counts'], len(speed), 'limit changes')


if __name__ == '__main__':
    main()

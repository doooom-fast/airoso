"""Bare-earth elevation along the Denver Grand Prix lap (PLAN section 5, P0; dossier section 3).

The lap is data/lap_line.plan.json (OSM nodes in driving order, written by source/lap_route.py). It is resampled
every STEP_M along OSM's lines and sampled on USGS 3DEP through the engine's own sampler
(scripts.elevation.usgs_3dep.sample_points: the 3DEPElevation ImageServer's getSamples, best available resolution).
3DEP is BARE EARTH: on a bridge it reads the creek bed, under a roof it reads whatever the classifier left as ground.
Nothing here is smoothed into the file; the report's grades are read from a SMOOTH_M running mean and say so.

    python3 tracks/denver-grand-prix/source/elevation/lap_profile.py          # from the repo root; fetches
    python3 tracks/denver-grand-prix/source/elevation/lap_profile.py report   # re-reads the file, no network

Writes tracks/denver-grand-prix/data/lap_profile.3dep.json and prints the report.
"""
import json, math, os, sys, time, urllib.parse, urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), *[os.pardir] * 4))
sys.path.insert(0, ROOT)
from scripts.tls import https_context  # noqa: E402
from scripts.elevation import usgs_3dep  # noqa: E402

T = os.path.join(ROOT, 'tracks', 'denver-grand-prix')
OUT = os.path.join(T, 'data', 'lap_profile.3dep.json')
LON0, LAT0 = -104.9849, 39.7401           # the plan's frame: metres east / north of the Colfax / Sherman crosswalk
STEP_M = 2.0
SMOOTH_M = 30.0                            # running mean the grades are read from (the raw 1 m DEM crosses kerbs and medians)


def xy(lon, lat):
    return (lon - LON0) * 111320 * math.cos(math.radians(LAT0)), (lat - LAT0) * 110950


def resample():
    nodes = json.load(open(os.path.join(T, 'data', 'lap_line.plan.json')))['nodes']
    out = []; s = 0.0; nxt = 0.0
    for a, b in zip(nodes, nodes[1:]):
        L = math.dist(xy(a['lon'], a['lat']), xy(b['lon'], b['lat']))
        while nxt <= s + L and L > 0:
            t = (nxt - s) / L
            out.append({'s': round(nxt, 2), 'lon': a['lon'] + (b['lon'] - a['lon']) * t, 'lat': a['lat'] + (b['lat'] - a['lat']) * t,
                        'leg': b['leg'], 'way': b['way']})
            nxt += STEP_M
        s += L
    return out, s


def resolutions(pts):
    """the cell size 3DEP answered from, on every 25th sample (the engine's sampler drops this field)"""
    sub = pts[::25]
    body = urllib.parse.urlencode({'geometry': json.dumps({'points': [[p['lon'], p['lat']] for p in sub], 'spatialReference': {'wkid': 4326}}),
                                   'geometryType': 'esriGeometryMultipoint', 'returnFirstValueOnly': 'true', 'f': 'json'}).encode()
    req = urllib.request.Request(usgs_3dep.GET_SAMPLES, data=body, headers={'User-Agent': 'airoso/0.1'})
    sm = None
    for k in range(5):                      # the service answers 502 / 504 when busy
        try:
            with urllib.request.urlopen(req, timeout=150, context=https_context()) as r:
                sm = json.loads(r.read().decode()).get('samples', [])
            break
        except Exception:                   # noqa: BLE001
            time.sleep(5 * (k + 1))
    if sm is None:
        return {'not read (service error)': len(sub)}, len(sub)
    res = {}
    for q in sm:
        res[q.get('resolution')] = res.get(q.get('resolution'), 0) + 1
    return res, len(sub)


def fetch():
    pts, total = resample()
    z = usgs_3dep.sample_points([(p['lon'], p['lat']) for p in pts], retries=6)
    res, n = resolutions(pts)
    for p, e in zip(pts, z):
        p['z'] = round(e, 3); p['lon'] = round(p['lon'], 7); p['lat'] = round(p['lat'], 7)
        p['x'], p['y'] = (round(v, 1) for v in xy(p['lon'], p['lat']))
    json.dump({'_doc': 'USGS 3DEP bare-earth elevation (m, NAVD88) every %.0f m along the Denver Grand Prix lap on OSM\'s lines, from S/F '
                       'round to S/F. s = metres from the Colfax / Sherman crosswalk; x, y = metres east / north of it. BARE EARTH: '
                       'bridges read the ground beneath them. Not smoothed. Script: source/elevation/lap_profile.py.' % STEP_M,
               'source': usgs_3dep.GET_SAMPLES, 'fetched_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
               'resolution_m_counts_on_every_25th_sample': {str(k): v for k, v in res.items()}, 'resolution_samples': n,
               'lap_length_m': round(total, 1), 'step_m': STEP_M, 'points': pts}, open(OUT, 'w'), separators=(',', ':'))


def smooth(z, w):
    n = len(z); out = []
    for i in range(n):
        a = max(0, i - w); b = min(n, i + w + 1)
        out.append(sum(z[a:b]) / (b - a))
    return out


def report():
    d = json.load(open(OUT)); P = d['points']; z = [p['z'] for p in P]; n = len(P)
    w = int(SMOOTH_M / d['step_m'] / 2); zs = smooth(z, w)
    print(f"lap {d['lap_length_m']} m, {n} samples every {d['step_m']} m, 3DEP cell sizes {d['resolution_m_counts_on_every_25th_sample']} "
          f"(on {d['resolution_samples']} samples), fetched {d['fetched_utc']}")
    hi = max(range(n), key=lambda i: z[i]); lo = min(range(n), key=lambda i: z[i])
    print(f"raw: highest {z[hi]:.1f} m at s {P[hi]['s']:.0f} ({P[hi]['leg']}); lowest {z[lo]:.1f} m at s {P[lo]['s']:.0f} ({P[lo]['leg']}); "
          f"relief {z[hi] - z[lo]:.1f} m")
    print(f"S/F {z[0]:.1f} m")
    print('\nper leg (grades from the %.0f m running mean; + = climbing in the driving direction):' % SMOOTH_M)
    legs = []
    for i, p in enumerate(P):
        if not legs or legs[-1][0] != p['leg']:
            legs.append([p['leg'], i, i])
        legs[-1][2] = i
    g = int(50 / d['step_m'])
    for name, a, b in legs:
        L = P[b]['s'] - P[a]['s']; seg = z[a:b + 1]
        gr = [(zs[i + g] - zs[i]) / 50 * 100 for i in range(a, b - g + 1)] or [0.0]
        st = max(range(len(gr)), key=lambda k: abs(gr[k]))
        print(f"  {name:32s} s {P[a]['s']:6.0f}-{P[b]['s']:6.0f}  {zs[a]:7.1f} -> {zs[b]:7.1f} m  mean {((zs[b] - zs[a]) / L * 100 if L else 0):+5.2f} %  "
              f"steepest 50 m {gr[st]:+5.2f} % at s {P[a + st]['s']:.0f}  raw min {min(seg):.1f} max {max(seg):.1f}")
    # where bare earth leaves the road: the raw profile against a 60 m chord, both ends on the smooth profile
    print('\nwhere bare earth drops or rises more than 1.5 m from a 60 m chord (bridges, the roofed section, walls):')
    c = int(30 / d['step_m']); runs = []
    for i in range(n):
        a = max(0, i - c); b = min(n - 1, i + c)
        ch = z[a] + (z[b] - z[a]) * ((i - a) / (b - a))
        dv = z[i] - ch
        if abs(dv) > 1.5:
            if runs and i - runs[-1][1] <= c:
                runs[-1][1] = i; runs[-1][2] = min(runs[-1][2], dv); runs[-1][3] = max(runs[-1][3], dv)
            else:
                runs.append([i, i, dv, dv])
    for a, b, mn, mx in runs:
        print(f"  s {P[a]['s']:6.0f}-{P[b]['s']:6.0f} ({P[b]['s'] - P[a]['s']:4.0f} m)  x {P[a]['x']:7.0f},{P[a]['y']:6.0f} -> {P[b]['x']:7.0f},{P[b]['y']:6.0f}  "
              f"{P[a]['leg']:30s} way {P[a]['way']}  dev {mn:+.1f} .. {mx:+.1f} m")
    return d


if __name__ == '__main__':
    if not (len(sys.argv) > 1 and sys.argv[1] == 'report'):
        fetch()
    report()

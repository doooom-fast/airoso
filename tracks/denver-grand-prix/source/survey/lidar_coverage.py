"""What the CO_DRCOG_2_2020 lidar holds along the Denver Grand Prix lap (PLAN section 4b; dossier sections 3 and 9).

Reads every return of the dataset's public EPT (all depths) in the nodes that touch a HALF_M corridor round the lap
(data/lap_profile.3dep.json's 2 m samples), the way tools/lidar_buildings.py walks it, and counts on a 1 m grid in the
plan's frame (metres east / north of the Colfax / Sherman crosswalk). It reports density per true square metre, the
class mix, the flight dates (from GpsTime), and what stands at the places 3DEP's bare earth cannot describe: the two
creek bridges, the roofed stretch of Stout, and the hole on 15th St. It measures coverage; it stands no pole and
draws no paint.

    python3 tracks/denver-grand-prix/source/survey/lidar_coverage.py <cache-dir>     # cache: the .laz nodes, NOT in git

Needs numpy, laspy with lazrs. Writes lidar_coverage.json beside this file.
"""
import concurrent.futures as cf, datetime, io, json, math, os, sys, time, urllib.request
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), *[os.pardir] * 4))
sys.path.insert(0, ROOT)
from scripts.tls import https_context  # noqa: E402

EPT = 'https://s3-us-west-2.amazonaws.com/usgs-lidar-public/CO_DRCOG_2_2020/ept.json'
BASE = EPT.rsplit('/', 1)[0]
T = os.path.join(ROOT, 'tracks', 'denver-grand-prix')
LON0, LAT0 = -104.9849, 39.7401
HALF_M = 15.0           # the corridor counted: this far either side of OSM's line
RM = 6378137.0


def get(url):
    for k in range(5):
        try:
            with urllib.request.urlopen(url, timeout=180, context=https_context()) as r:
                return r.read()
        except Exception:               # noqa: BLE001
            if k == 4:
                raise
            time.sleep(2 + 3 * k)


def to3857(lon, lat):
    return RM * np.radians(lon), RM * np.log(np.tan(np.pi / 4 + np.radians(lat) / 2))


def local(X, Y):
    lon = np.degrees(X / RM); lat = np.degrees(2 * np.arctan(np.exp(Y / RM)) - np.pi / 2)
    return (lon - LON0) * 111320 * math.cos(math.radians(LAT0)), (lat - LAT0) * 110950


def main(cache):
    import laspy
    os.makedirs(cache, exist_ok=True)
    prof = json.load(open(os.path.join(T, 'data', 'lap_profile.3dep.json')))['points']
    LX, LY = to3857(np.array([p['lon'] for p in prof]), np.array([p['lat'] for p in prof]))
    k = 1 / math.cos(math.radians(LAT0)); pad = (HALF_M + 5) * k
    ept = json.loads(get(EPT)); b = ept['bounds']; hier = {}

    def h_of(key):
        if key not in hier:
            hier[key] = json.loads(get(f'{BASE}/ept-hierarchy/{key}.json'))
        return hier[key]
    keys = {}

    def walk(d, x, y, z, h):
        key = f'{d}-{x}-{y}-{z}'
        if key not in h:
            return
        if h[key] == -1:
            h = h_of(key)
        sz = (b[3] - b[0]) / 2 ** d; bx, by = b[0] + x * sz, b[1] + y * sz
        if not ((LX > bx - pad) & (LX < bx + sz + pad) & (LY > by - pad) & (LY < by + sz + pad)).any():
            return
        if h[key] > 0:
            keys[key] = h[key]
        for dx in (0, 1):
            for dy in (0, 1):
                for dz in (0, 1):
                    walk(d + 1, 2 * x + dx, 2 * y + dy, 2 * z + dz, h)
    walk(0, 0, 0, 0, h_of('0-0-0-0'))
    print(f'{len(keys)} nodes, {sum(keys.values()):,} points, depths {min(int(q.split("-")[0]) for q in keys)}-{max(int(q.split("-")[0]) for q in keys)}')

    def node(key):
        p = os.path.join(cache, key + '.laz')
        if not os.path.exists(p):
            open(p + '.part', 'wb').write(get(f'{BASE}/ept-data/{key}.laz')); os.replace(p + '.part', p)
        las = laspy.read(p)
        x, y = local(np.asarray(las.x), np.asarray(las.y))
        return (x.astype(np.float32), y.astype(np.float32), np.asarray(las.z, np.float32), np.asarray(las.classification, np.uint8),
                np.asarray(las.intensity, np.uint16), np.asarray(las.gps_time), np.asarray(las.return_number, np.uint8), os.path.getsize(p))
    with cf.ThreadPoolExecutor(8) as ex:
        parts = list(ex.map(node, sorted(keys)))
    nbytes = sum(p[7] for p in parts)
    x, y, z, c, inten, t, rn = (np.concatenate([p[i] for p in parts]) for i in range(7))
    # nearest lap sample for every return within the corridor: a 1 m grid of "which sample is nearest"
    px = np.array([p['x'] for p in prof]); py = np.array([p['y'] for p in prof])
    x0, y0 = px.min() - 40, py.min() - 40; W = int(px.max() - x0 + 40); H = int(py.max() - y0 + 40)
    near = np.full((H, W), -1, np.int32); dist = np.full((H, W), 1e9, np.float32)
    r = int(HALF_M) + 1; oy, ox = np.mgrid[-r:r + 1, -r:r + 1]
    for i, (ax, ay) in enumerate(zip(px, py)):
        cx, cy = int(ax - x0), int(ay - y0)
        d = np.hypot(ox + cx + 0.5 - (ax - x0), oy + cy + 0.5 - (ay - y0)).astype(np.float32)
        sl = (slice(cy - r, cy + r + 1), slice(cx - r, cx + r + 1))
        m = d < dist[sl]; dist[sl][m] = d[m]; near[sl][m] = i
    near[dist > HALF_M] = -1
    ix = (x - x0).astype(int); iy = (y - y0).astype(int)
    ok = (ix >= 0) & (ix < W) & (iy >= 0) & (iy < H)
    st = np.full(len(x), -1, np.int32); st[ok] = near[iy[ok], ix[ok]]
    m = st >= 0
    x, y, z, c, inten, t, rn, st = (a[m] for a in (x, y, z, c, inten, t, rn, st))
    area = float((near >= 0).sum())                                          # true square metres of corridor
    cls = {int(v): int(n) for v, n in zip(*np.unique(c, return_counts=True))}
    gps0 = datetime.datetime(1980, 1, 6)
    days = sorted({(gps0 + datetime.timedelta(seconds=float(s) + 1e9)).date().isoformat() for s in np.unique(np.round(t / 3600) * 3600)})
    n = len(prof); cell = np.bincount(near[near >= 0], minlength=n).astype(float)   # m2 of corridor nearest each sample
    cnt = lambda mask: np.bincount(st[mask], minlength=n).astype(float)
    alln, gnd, brd = cnt(np.ones(len(st), bool)), cnt(c == 2), cnt(c == 17)
    zprof = np.array([p['z'] for p in prof]); s = np.array([p['s'] for p in prof])
    above = z - zprof[st]                                                    # height over 3DEP bare earth at the nearest sample

    def span(a, bq, note):
        q = (s >= a) & (s <= bq); pm = q[st]
        A = cell[q].sum() or 1
        hi = above[pm]; cc = c[pm]
        o = {'s': [a, bq], 'what': note, 'corridor_m2': int(A), 'returns_per_m2': round(float(alln[q].sum() / A), 1),
             'ground_class2_per_m2': round(float(gnd[q].sum() / A), 2), 'bridge_deck_class17_per_m2': round(float(brd[q].sum() / A), 2),
             'classes': {int(v): int(k2) for v, k2 in zip(*np.unique(cc, return_counts=True))},
             'height_over_3dep_m_percentiles_5_50_95': [round(float(v), 1) for v in np.percentile(hi, [5, 50, 95])] if len(hi) else None}
        for name, code in (('ground_class2', 2), ('bridge_deck_class17', 17)):
            hh = hi[cc == code]
            o[name + '_height_over_3dep_m_5_50_95'] = [round(float(v), 1) for v in np.percentile(hh, [5, 50, 95])] if len(hh) else None
        return o
    legs = []
    for p in prof:
        if not legs or legs[-1][0] != p['leg']:
            legs.append([p['leg'], p['s'], p['s']])
        legs[-1][2] = p['s']
    w = 5                                                                      # 10 m windows for the "thin" test
    roll = np.convolve(alln, np.ones(w), 'same') / np.maximum(np.convolve(cell, np.ones(w), 'same'), 1)
    groll = np.convolve(gnd + brd, np.ones(w), 'same') / np.maximum(np.convolve(cell, np.ones(w), 'same'), 1)
    def runs(mask):
        out = []; i = 0
        while i < n:
            if mask[i]:
                j = i
                while j + 1 < n and mask[j + 1]:
                    j += 1
                if s[j] - s[i] >= 10:
                    out.append([float(s[i]), float(s[j])])
                i = j + 1
            else:
                i += 1
        return out
    rep = {'_doc': 'CO_DRCOG_2_2020 lidar within %.0f m of the Denver Grand Prix lap on OSM\'s lines: every return of every EPT node that '
                   'touches the corridor. Densities are per true square metre. Heights are over the 3DEP bare-earth value at the nearest lap '
                   'sample. Written by lidar_coverage.py.' % HALF_M,
           'ept': EPT, 'ept_points_total': ept['points'], 'read_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
           'nodes': len(keys), 'node_bytes': nbytes, 'returns_in_nodes': int(sum(keys.values())), 'returns_in_corridor': int(len(st)),
           'corridor_m2': int(area), 'returns_per_m2': round(len(st) / area, 1), 'first_returns_per_m2': round(float((rn == 1).sum()) / area, 1),
           'ground_class2_per_m2': round(float((c == 2).sum()) / area, 2),
           'classes': cls, 'flight_dates_utc': days, 'intensity_percentiles_1_50_99': [int(v) for v in np.percentile(inten, [1, 50, 99])],
           'ground_intensity_percentiles_1_50_99': [int(v) for v in np.percentile(inten[c == 2], [1, 50, 99])],
           'lap_m_with_under_2_returns_per_m2': runs(roll < 2), 'lap_m_with_no_ground_or_deck_return_in_10_m': runs(groll <= 0),
           'legs': [span(a, bq, name) for name, a, bq in legs],
           'spots': [span(2784, 2814, 'Blake St bridge over Cherry Creek (OSM way 461500433)'),
                     span(4888, 4930, 'W 14th Ave bridge over Cherry Creek (OSM way 44932761)'),
                     span(1390, 1734, 'Stout St under the Convention Center (OSM building_passage ways)'),
                     span(2284, 2316, '15th St: the 5 m hole in 3DEP bare earth short of Lawrence St')]}
    json.dump(rep, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lidar_coverage.json'), 'w'), indent=1)
    print(json.dumps({k2: v for k2, v in rep.items() if k2 not in ('legs',)}, indent=1))
    for L in rep['legs']:
        print(f"{L['what']:32s} {L['returns_per_m2']:6.1f} /m2  ground {L['ground_class2_per_m2']:5.2f}  deck {L['bridge_deck_class17_per_m2']:5.2f}")


if __name__ == '__main__':
    main(sys.argv[1])

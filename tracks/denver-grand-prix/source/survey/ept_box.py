"""Every CO_DRCOG_2_2020 return in a lon / lat box, from the public EPT (all depths), cached as the .laz nodes.

    from ept_box import points
    P = points((w, s, e, n), cache_dir)      # dict of numpy arrays: lon, lat, z, cls, intensity, rn, nr

    python3 ept_box.py <w> <s> <e> <n> <cache-dir> <out.npz>

The walk is tools/lidar_buildings.py's (hierarchy pages on demand, nodes that touch the box). Nothing is thinned.
Needs numpy and laspy with lazrs. The point cloud stays out of git.
"""
import concurrent.futures as cf, json, os, sys, time, urllib.request
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), *[os.pardir] * 4))
sys.path.insert(0, ROOT)
from scripts.tls import https_context  # noqa: E402

EPT = 'https://s3-us-west-2.amazonaws.com/usgs-lidar-public/CO_DRCOG_2_2020/ept.json'
BASE = EPT.rsplit('/', 1)[0]
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


def points(box, cache):
    import laspy
    os.makedirs(cache, exist_ok=True)
    w, s, e, n = box
    X0, X1 = RM * np.radians(w), RM * np.radians(e)
    Y0, Y1 = (RM * np.log(np.tan(np.pi / 4 + np.radians(v) / 2)) for v in (s, n))
    ept = json.loads(get(EPT)); b = ept['bounds']; hier = {}; keys = []

    def h_of(key):
        if key not in hier:
            p = os.path.join(cache, f'hier-{key}.json')
            if not os.path.exists(p):
                open(p, 'wb').write(get(f'{BASE}/ept-hierarchy/{key}.json'))
            hier[key] = json.load(open(p))
        return hier[key]

    def walk(d, x, y, z, h):
        key = f'{d}-{x}-{y}-{z}'
        if key not in h:
            return
        if h[key] == -1:
            h = h_of(key)
        sz = (b[3] - b[0]) / 2 ** d; bx, by = b[0] + x * sz, b[1] + y * sz
        if bx > X1 or bx + sz < X0 or by > Y1 or by + sz < Y0:
            return
        if h[key] > 0:
            keys.append(key)
        for dx in (0, 1):
            for dy in (0, 1):
                for dz in (0, 1):
                    walk(d + 1, 2 * x + dx, 2 * y + dy, 2 * z + dz, h)
    walk(0, 0, 0, 0, h_of('0-0-0-0'))

    def node(key):
        p = os.path.join(cache, key + '.laz')
        if not os.path.exists(p):
            open(p + '.part', 'wb').write(get(f'{BASE}/ept-data/{key}.laz')); os.replace(p + '.part', p)
        las = laspy.read(p); x = np.asarray(las.x); y = np.asarray(las.y)
        m = (x >= X0) & (x <= X1) & (y >= Y0) & (y <= Y1)
        return (np.degrees(x[m] / RM), np.degrees(2 * np.arctan(np.exp(y[m] / RM)) - np.pi / 2), np.asarray(las.z)[m],
                np.asarray(las.classification)[m], np.asarray(las.intensity)[m], np.asarray(las.return_number)[m],
                np.asarray(las.number_of_returns)[m], np.asarray(las.gps_time)[m])
    with cf.ThreadPoolExecutor(8) as ex:
        parts = list(ex.map(node, sorted(keys)))
    names = ('lon', 'lat', 'z', 'cls', 'intensity', 'rn', 'nr', 't')
    out = {k: np.concatenate([p[i] for p in parts]) for i, k in enumerate(names)}
    out['nodes'] = len(keys)
    return out


if __name__ == '__main__':
    a = sys.argv
    P = points(tuple(float(v) for v in a[1:5]), a[5])
    np.savez_compressed(a[6], **{k: v for k, v in P.items() if k != 'nodes'})
    print(len(P['z']), 'returns in', P['nodes'], 'nodes ->', a[6])

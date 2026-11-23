"""Fetch what the lap survey reads, into a cache directory that stays out of git.

    python3 lap_fetch.py <cache-dir> [--years 2022,2020,2018] [--lidar] [--naip]

Aerials: DRCOG's 3-inch archive (drapp_mosaic.py's method, HTTP Range on uncompressed tiles), but each archive tile's
rows are fetched once into a sparse local copy (<cache>/drapp/<year>_<tile>.raw + .rows.npy) and every work tile
(lapgeo.tiles()) is cut from those: <cache>/img/<year>/<tile-id>.png with the bbox sidecar the aerial engine reads.
Only the rows a work tile needs are requested; no whole archive tile is downloaded unless the lap needs all its rows.
Lidar: CO_DRCOG_2_2020 through ept_box.points per work tile: <cache>/lidar/<tile-id>.npz.
Writes <cache>/fetch_<year>.json (archive tiles used, rows and bytes fetched, date read): the provenance SURVEY.md cites.
"""
import concurrent.futures as cf, json, math, os, re, struct, sys, time, urllib.parse, urllib.request
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import lapgeo  # noqa: E402
from scripts.tls import https_context  # noqa: E402

B = 'https://drapparchive.s3.amazonaws.com/'
PX = 0.25; TILE_PX = 10560
FETCHED = [0]


def get(url, a=None, b=None, tries=7):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={'Range': f'bytes={a}-{b}'} if a is not None else {})
            with urllib.request.urlopen(req, timeout=300, context=https_context()) as r:
                d = r.read(); FETCHED[0] += len(d); return d
        except Exception:           # noqa: BLE001
            if k == tries - 1:
                raise
            time.sleep(2 + 3 * k)


def archive_tiles(year, cache):
    """name -> outer edges (x0, y1) in State Plane ft of every S1 / N1 archive tile at 0.25 ft, from the world files."""
    p = os.path.join(cache, f'drapp_index_{year}.json')
    if os.path.exists(p):
        return json.load(open(p))
    keys = [];
    for pre in ('N1E', 'N1W', 'S1E', 'S1W'):
        tok = None
        while True:
            q = {'list-type': '2', 'max-keys': '1000', 'prefix': f'{year}/{pre}'}
            if tok:
                q['continuation-token'] = tok
            t = get(B + '?' + urllib.parse.urlencode(q)).decode(); keys += re.findall(r'<Key>([^<]+\.tfw)</Key>', t)
            m = re.search(r'<NextContinuationToken>([^<]+)<', t)
            if not m:
                break
            tok = m.group(1)
    def one(k):
        a = [float(v) for v in get(B + k).decode().split()]
        return (k.split('/')[-1][:-4], a)
    with cf.ThreadPoolExecutor(8) as ex:
        res = dict(ex.map(one, keys))
    out = {n: [a[4] - PX / 2, a[5] + PX / 2] for n, a in res.items() if len(a) == 6 and abs(a[0] - PX) < 1e-9}
    json.dump(out, open(p, 'w')); return out


class Tile:
    def __init__(self, year, name, cache):
        self.url = f'{B}{year}/{name}.tif'; self.name = name
        self.raw = os.path.join(cache, 'drapp', f'{year}_{name}.raw'); self.rowsf = self.raw + '.rows.npy'; self.meta = self.raw + '.json'
        os.makedirs(os.path.dirname(self.raw), exist_ok=True)
        if os.path.exists(self.meta):
            m = json.load(open(self.meta))
        else:
            head = get(self.url, 0, 15); bo = '<' if head[:2] == b'II' else '>'
            off = struct.unpack(bo + 'I', head[4:8])[0]; n = struct.unpack(bo + 'H', get(self.url, off, off + 1))[0]
            raw = get(self.url, off + 2, off + 2 + n * 12 - 1); tags = {}; size = {1: 1, 3: 2, 4: 4}; fmt = {1: 'B', 3: 'H', 4: 'I'}
            for i in range(n):
                tag, typ, cnt = struct.unpack(bo + 'HHI', raw[i * 12:i * 12 + 8]); val = raw[i * 12 + 8:i * 12 + 12]
                if typ not in fmt:
                    continue
                if size[typ] * cnt > 4:
                    o = struct.unpack(bo + 'I', val)[0]; val = get(self.url, o, o + size[typ] * cnt - 1)
                tags[tag] = struct.unpack(bo + str(cnt) + fmt[typ], val[:size[typ] * cnt])
            if tags[259][0] != 1 or 273 not in tags:
                raise SystemExit(self.url + ': not an uncompressed stripped TIFF')
            m = {'W': tags[256][0], 'H': tags[257][0], 'spp': tags[277][0], 'rps': tags.get(278, (tags[257][0],))[0], 'offs': list(tags[273])}
            json.dump(m, open(self.meta, 'w'))
        self.W, self.H, self.spp, self.rps, self.offs = m['W'], m['H'], m['spp'], m['rps'], m['offs']
        self.rows = np.load(self.rowsf) if os.path.exists(self.rowsf) else np.zeros(self.H, bool)
        self.mm = np.memmap(self.raw, np.uint8, 'r+' if os.path.exists(self.raw) else 'w+', shape=(self.H, self.W, self.spp))

    def need(self, r0, r1):
        todo = np.nonzero(~self.rows[r0:r1])[0] + r0
        if not len(todo):
            return
        runs = np.split(todo, np.nonzero(np.diff(todo) > 1)[0] + 1); jobs = []
        for run in runs:
            for i in range(run[0], run[-1] + 1, 256):
                jobs.append((i, min(i + 256, run[-1] + 1)))
        def one(j):
            a, b = j; o0 = self.offs[a // self.rps] + (a % self.rps) * self.W * self.spp
            o1 = self.offs[(b - 1) // self.rps] + ((b - 1) % self.rps) * self.W * self.spp
            if o1 - o0 != (b - 1 - a) * self.W * self.spp:
                raise SystemExit(self.name + ': strips are not contiguous')
            d = get(self.url, o0, o1 + self.W * self.spp - 1)
            self.mm[a:b] = np.frombuffer(d, np.uint8).reshape(b - a, self.W, self.spp); self.rows[a:b] = True
        with cf.ThreadPoolExecutor(6) as ex:
            list(ex.map(one, jobs))
        self.mm.flush(); np.save(self.rowsf, self.rows)


def sp_box(box):
    from pyproj import Transformer
    T = Transformer.from_crs(4326, 2232, always_xy=True)
    lo, la = lapgeo.lonlat([box[0], box[0], box[2], box[2]], [box[1], box[3], box[1], box[3]]); X, Y = T.transform(lo, la)
    X0 = math.floor(min(X) / PX) * PX + 0.125; Y0 = math.floor(min(Y) / PX) * PX + 0.125     # the archive's own pixel grid
    W = int(round((max(X) - X0) / PX)); H = int(round((max(Y) - Y0) / PX))
    return X0, Y0, W, H


def aerials(year, cache):
    idx = archive_tiles(year, cache); span = TILE_PX * PX; opened = {}; used = {}
    os.makedirs(os.path.join(cache, 'img', str(year)), exist_ok=True)
    for wt in lapgeo.tiles():
        out = os.path.join(cache, 'img', str(year), wt['id'] + '.png')
        if os.path.exists(out) and os.path.exists(out[:-4] + '.json'):
            continue
        X0, Y0, W, H = sp_box(wt['box']); X1, Y1 = X0 + W * PX, Y0 + H * PX
        img = np.zeros((H, W, 3), np.uint8); got = np.zeros((H, W), bool); parts = []
        for name, (tx0, ty1) in idx.items():
            if tx0 >= X1 or tx0 + span <= X0 or ty1 <= Y0 or ty1 - span >= Y1:
                continue
            t = opened.get(name) or opened.setdefault(name, Tile(year, name, cache))
            c0 = int(round((X0 - tx0) / PX)); r0 = int(round((ty1 - Y1) / PX))
            a0, a1 = max(0, c0), min(t.W, c0 + W); b0, b1 = max(0, r0), min(t.H, r0 + H)
            if a1 <= a0 or b1 <= b0:
                continue
            t.need(b0, b1)
            img[b0 - r0:b1 - r0, a0 - c0:a1 - c0] = t.mm[b0:b1, a0:a1, :3]; got[b0 - r0:b1 - r0, a0 - c0:a1 - c0] = True
            parts.append({'tile': name, 'url': t.url, 'rows': [b0, b1], 'cols': [a0, a1]}); used[name] = t
        Image.fromarray(img).save(out, compress_level=1)
        json.dump({'kind': 'bbox', 'bbox_ftus': [X0, Y0, X1, Y1], 'crs': 'EPSG:2232 (inferred from the tiles\' world files)', 'size': [W, H], 'pixel_ft': PX,
                   'source': f'DRCOG aerial archive, {B}{year}/', 'tiles': parts, 'uncovered_px': int((~got).sum()), 'work_tile': wt,
                   'read_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}, open(out[:-4] + '.json', 'w'), indent=1)
        print(year, wt['id'], W, 'x', H, [p['tile'] for p in parts], 'uncovered', int((~got).sum()), FETCHED[0] // 1000000, 'MB so far', flush=True)
    prov = {'year': year, 'bucket': B, 'read_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'bytes_fetched_this_run': FETCHED[0],
            'archive_tiles': {n: {'url': t.url, 'rows_fetched': int(t.rows.sum()), 'rows_in_tile': t.H, 'bytes': int(t.rows.sum()) * t.W * t.spp} for n, t in sorted(used.items())}}
    if used:
        json.dump(prov, open(os.path.join(cache, f'fetch_{year}.json'), 'w'), indent=1)


def lidar(cache):
    import ept_box
    os.makedirs(os.path.join(cache, 'lidar'), exist_ok=True)
    for wt in lapgeo.tiles():
        out = os.path.join(cache, 'lidar', wt['id'] + '.npz')
        if os.path.exists(out):
            continue
        (w, e), (s, n) = lapgeo.lonlat([wt['box'][0], wt['box'][2]], [wt['box'][1], wt['box'][3]])
        P = ept_box.points((w, s, e, n), os.path.join(cache, 'ept'))
        np.savez_compressed(out, **{k: v for k, v in P.items() if k != 'nodes'}); print('lidar', wt['id'], len(P['z']), 'returns', P['nodes'], 'nodes', flush=True)


if __name__ == '__main__':
    a = sys.argv; cache = a[1]
    years = a[a.index('--years') + 1].split(',') if '--years' in a else []
    for y in years:
        aerials(int(y), cache)
    if '--lidar' in a:
        lidar(cache)

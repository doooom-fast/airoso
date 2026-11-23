"""Which tiles of DRCOG's aerial archive (the Denver Regional Aerial Photography Project) cover the Denver Grand Prix lap,
and which years can be downloaded without an account (PLAN section 4b, "which year we can get is P0's first check").

The archive is a public S3 bucket, https://drapparchive.s3.amazonaws.com/ : one prefix per flight year, GeoTIFF tiles
with ESRI world files, Colorado State Plane Central, US feet (EPSG:2232, read off the world files' coordinates: not
stated in the bucket). This lists each year, reads the world files of every S1 and N1 tile (the two rows of blocks the lap is in), keeps
the tiles the lap's 2 m samples fall in, and asks for the first 100 bytes of one tile per year to see whether the
bucket hands it out (206) or refuses (403). It downloads no imagery.

    python3 tracks/denver-grand-prix/source/survey/drapp_tiles.py      # writes drapp_tiles.json beside this file

Needs pyproj.
"""
import concurrent.futures as cf, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), *[os.pardir] * 4))
sys.path.insert(0, ROOT)
from scripts.tls import https_context  # noqa: E402

B = 'https://drapparchive.s3.amazonaws.com/'
YEARS = ['2016/', '2018/', '2020/', '2022/', '2024/3inch/', '2024/6inch/']
TILE_PX = 10560            # 446 MB = 10560 x 10560 x 4 bytes, uncompressed (the size every tile has)


def get(url, rng=None):
    for k in range(6):
        try:
            req = urllib.request.Request(url, headers={'Range': rng} if rng else {})
            with urllib.request.urlopen(req, timeout=90, context=https_context()) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):
                return e.code, b''
            time.sleep(2 + 2 * k)
        except Exception:           # noqa: BLE001  (resets when asked too fast)
            time.sleep(2 + 2 * k)
    raise SystemExit('no answer: ' + url)


def ls(prefix):
    tok = None; keys = []
    while True:
        q = {'list-type': '2', 'max-keys': '1000', 'prefix': prefix}
        if tok:
            q['continuation-token'] = tok
        t = get(B + '?' + urllib.parse.urlencode(q))[1].decode()
        keys += [(k, m, int(s)) for k, m, s in re.findall(r'<Key>([^<]+)</Key><LastModified>([^<]+)</LastModified>.*?<Size>(\d+)</Size>', t)]
        m = re.search(r'<NextContinuationToken>([^<]+)<', t)
        if not m:
            return keys
        tok = m.group(1)


def main():
    from pyproj import Transformer
    T = Transformer.from_crs(4326, 2232, always_xy=True); Ti = Transformer.from_crs(2232, 4326, always_xy=True)
    P = json.load(open(os.path.join(ROOT, 'tracks', 'denver-grand-prix', 'data', 'lap_profile.3dep.json')))['points']
    xy = [T.transform(p['lon'], p['lat']) for p in P]
    out = {'_doc': 'DRCOG aerial archive tiles over the Denver Grand Prix lap, per flight year. download = the HTTP status of a ranged GET '
                   'of one tile (206 = handed out, 403 = refused). Coordinates: Colorado State Plane Central, US ft (EPSG:2232, inferred). '
                   'No imagery was downloaded. Written by drapp_tiles.py.', 'bucket': B, 'read_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'years': {}}
    for pre in YEARS:
        keys = ls(pre); have = {k[0].split('/')[-1]: k for k in keys}
        tifs = [k for k in keys if k[0].endswith('.tif')]
        yr = {'tiles_in_year': len(tifs), 'bytes_in_year': sum(k[2] for k in tifs), 'uploaded': [min(k[1] for k in tifs), max(k[1] for k in tifs)]}
        yr['download'] = get(B + tifs[0][0], 'bytes=0-99')[0]
        names = [n for n in have if n.endswith('.tfw') and n[:3] in ('S1W', 'S1E', 'N1W', 'N1E')]
        rows = []
        if names and get(B + pre + names[0])[0] == 200:
            with cf.ThreadPoolExecutor(4) as ex:
                res = dict(zip(names, ex.map(lambda n: [float(v) for v in get(B + pre + n)[1].decode().split()], names)))
            yr['pixel_ft'] = sorted({abs(a[0]) for a in res.values()})
            for n, a in sorted(res.items()):
                if len(a) != 6:
                    continue
                span = TILE_PX * a[0]; x0 = a[4] - a[0] / 2; y1 = a[5] + a[0] / 2; x1 = x0 + span; y0 = y1 - span
                hit = sum(1 for X, Y in xy if x0 <= X < x1 and y0 <= Y < y1)
                if hit:
                    w, s_ = Ti.transform(x0, y0); e, n_ = Ti.transform(x1, y1); k = have[n[:-4] + '.tif']
                    rows.append({'tile': n[:-4], 'url': B + k[0], 'bytes': k[2], 'last_modified': k[1], 'pixel_ft': a[0],
                                 'state_plane_ft_x0_y0_x1_y1': [round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)],
                                 'lon_lat_w_s_e_n': [round(w, 6), round(s_, 6), round(e, 6), round(n_, 6)], 'lap_m_inside': hit * 2})
            yr['lap_m_covered'] = sum(r['lap_m_inside'] for r in rows); yr['lap_bytes'] = sum(r['bytes'] for r in rows)
        else:
            yr['world_files'] = 'refused (403), or no S1 / N1 tile in this prefix: tile positions not read'
        yr['lap_tiles'] = rows
        out['years'][pre] = yr
        print(f"{pre:12s} {yr['tiles_in_year']:6d} tiles {yr['bytes_in_year'] / 1e12:.2f} TB  download {yr['download']}  pixel {yr.get('pixel_ft')} ft  "
              f"lap: {len(rows)} tiles, {yr.get('lap_m_covered')} m, {yr.get('lap_bytes', 0) / 1e9:.2f} GB  {[r['tile'] for r in rows]}")
    json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'drapp_tiles.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()

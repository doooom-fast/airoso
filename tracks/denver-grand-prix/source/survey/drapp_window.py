"""A window out of one DRCOG archive tile without downloading the tile (the tiles are uncompressed GeoTIFFs, 446 MB each):
the TIFF directory is read from the end of the file, then only the rows needed are fetched with HTTP Range requests.

    python3 drapp_window.py <tile-url> <lon> <lat> <half-width-m> <half-height-m> <out.png>

Writes <out.png> and <out>.json (the tile, the window in State Plane ft and pixels, bytes fetched). Needs pyproj, numpy, Pillow.
"""
import json, os, struct, sys, time, urllib.request
import numpy as np
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), *[os.pardir] * 4))
sys.path.insert(0, ROOT)
from scripts.tls import https_context  # noqa: E402

FETCHED = [0]


def rng(url, a, b):
    for k in range(6):
        try:
            req = urllib.request.Request(url, headers={'Range': f'bytes={a}-{b}'})
            with urllib.request.urlopen(req, timeout=180, context=https_context()) as r:
                d = r.read(); FETCHED[0] += len(d); return d
        except Exception:           # noqa: BLE001
            if k == 5:
                raise
            time.sleep(2 + 2 * k)


def main(url, lon, lat, hw, hh, out):
    from pyproj import Transformer
    head = rng(url, 0, 15); bo = '<' if head[:2] == b'II' else '>'
    ifd = struct.unpack(bo + 'I', head[4:8])[0]
    n = struct.unpack(bo + 'H', rng(url, ifd, ifd + 1))[0]
    raw = rng(url, ifd + 2, ifd + 2 + n * 12 - 1); tags = {}
    size = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 12: 8}; fmt = {1: 'B', 3: 'H', 4: 'I', 12: 'd'}
    for i in range(n):
        tag, typ, cnt = struct.unpack(bo + 'HHI', raw[i * 12:i * 12 + 8]); val = raw[i * 12 + 8:i * 12 + 12]
        if typ not in fmt:
            continue
        if size[typ] * cnt > 4:
            off = struct.unpack(bo + 'I', val)[0]; val = rng(url, off, off + size[typ] * cnt - 1)
        tags[tag] = struct.unpack(bo + str(cnt) + fmt[typ], val[:size[typ] * cnt])
    W, H, spp, comp = tags[256][0], tags[257][0], tags[277][0], tags[259][0]
    if comp != 1 or 273 not in tags:
        raise SystemExit(f'not an uncompressed stripped TIFF (compression {comp}, tags {sorted(tags)})')
    rps = tags.get(278, (H,))[0]; offs = tags[273]
    tfw = [float(v) for v in rng(url[:-4] + '.tfw', 0, 200).decode().split()]
    X, Y = Transformer.from_crs(4326, 2232, always_xy=True).transform(lon, lat)
    ft = 1 / 0.3048006096; px = tfw[0]
    c0 = int((X - hw * ft - tfw[4]) / px); c1 = int((X + hw * ft - tfw[4]) / px)
    r0 = int((tfw[5] - (Y + hh * ft)) / px); r1 = int((tfw[5] - (Y - hh * ft)) / px)
    c0, c1, r0, r1 = max(0, c0), min(W, c1), max(0, r0), min(H, r1)
    if c1 <= c0 or r1 <= r0:
        raise SystemExit('the point is not in this tile')
    rows = []
    for r in range(r0, r1):                      # strips are contiguous in these files: one request per 256 rows
        rows.append(offs[r // rps] + (r % rps) * W * spp)
    blob = b''
    for i in range(0, len(rows), 256):
        a = rows[i]; b = rows[min(i + 255, len(rows) - 1)] + W * spp - 1
        if b - a + 1 != (min(i + 256, len(rows)) - i) * W * spp:
            raise SystemExit('strips are not contiguous')
        blob += rng(url, a, b)
    img = np.frombuffer(blob, np.uint8).reshape(r1 - r0, W, spp)[:, c0:c1, :3]
    Image.fromarray(img).save(out)
    json.dump({'tile': url, 'tile_px': [W, H], 'bands': spp, 'pixel_ft': px, 'window_px_c0_r0_c1_r1': [c0, r0, c1, r1],
               'centre_lon_lat': [lon, lat], 'half_m': [hw, hh], 'bytes_fetched': FETCHED[0],
               'read_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}, open(out[:-4] + '.json', 'w'), indent=1)
    print(out, img.shape, 'bytes fetched', FETCHED[0])


if __name__ == '__main__':
    a = sys.argv
    main(a[1], float(a[2]), float(a[3]), float(a[4]), float(a[5]), a[6])

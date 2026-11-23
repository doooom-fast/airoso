"""A georeferenced window of DRCOG's 3-inch aerials over a box in the plan's frame, mosaicked across tiles, read by HTTP
range (drapp_window.py's method: the tiles are uncompressed, so only the rows wanted are fetched).

    python3 drapp_mosaic.py <year> <x0> <y0> <x1> <y1> <out.png> --tiles S1E100b,N1E190d [...]

x, y: metres east / north of the Colfax / Sherman crosswalk (-104.9849, 39.7401), the frame PLAN.md and the lap files use.
Writes <out.png> (RGB) and <out>.json, a ``bbox`` sidecar scripts/aerial/engine/ortho.py reads
({"bbox_ftus": [xmin, ymin, xmax, ymax], "crs": "EPSG:2232", ...}) with the tiles, the bytes fetched and the date read.
The CRS is inferred from the world files' coordinates (Colorado State Plane Central, US ft); the registration check in
the survey is what tests it. Pixels no listed tile covers stay black and are counted. Needs pyproj, numpy, Pillow.
"""
import json, math, os, struct, sys, time, urllib.request
import numpy as np
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), *[os.pardir] * 4))
sys.path.insert(0, ROOT)
from scripts.tls import https_context  # noqa: E402

B = 'https://drapparchive.s3.amazonaws.com/'
LON0, LAT0 = -104.9849, 39.7401
FETCHED = [0]


def rng(url, a, b):
    for k in range(6):
        try:
            req = urllib.request.Request(url, headers={'Range': f'bytes={a}-{b}'})
            with urllib.request.urlopen(req, timeout=300, context=https_context()) as r:
                d = r.read(); FETCHED[0] += len(d); return d
        except Exception:           # noqa: BLE001
            if k == 5:
                raise
            time.sleep(2 + 2 * k)


def ifd(url):
    head = rng(url, 0, 15); bo = '<' if head[:2] == b'II' else '>'
    off = struct.unpack(bo + 'I', head[4:8])[0]
    n = struct.unpack(bo + 'H', rng(url, off, off + 1))[0]
    raw = rng(url, off + 2, off + 2 + n * 12 - 1); tags = {}
    size = {1: 1, 3: 2, 4: 4}; fmt = {1: 'B', 3: 'H', 4: 'I'}
    for i in range(n):
        tag, typ, cnt = struct.unpack(bo + 'HHI', raw[i * 12:i * 12 + 8]); val = raw[i * 12 + 8:i * 12 + 12]
        if typ not in fmt:
            continue
        if size[typ] * cnt > 4:
            o = struct.unpack(bo + 'I', val)[0]; val = rng(url, o, o + size[typ] * cnt - 1)
        tags[tag] = struct.unpack(bo + str(cnt) + fmt[typ], val[:size[typ] * cnt])
    if tags[259][0] != 1 or 273 not in tags:
        raise SystemExit(url + ': not an uncompressed stripped TIFF')
    return tags[256][0], tags[257][0], tags[277][0], tags.get(278, (tags[257][0],))[0], tags[273]


def main(year, x0, y0, x1, y1, out, tiles):
    from pyproj import Transformer
    T = Transformer.from_crs(4326, 2232, always_xy=True)
    kx = 111320 * math.cos(math.radians(LAT0))
    cs = [T.transform(LON0 + x / kx, LAT0 + y / 110950) for x in (x0, x1) for y in (y0, y1)]
    X0, X1 = min(c[0] for c in cs), max(c[0] for c in cs); Y0, Y1 = min(c[1] for c in cs), max(c[1] for c in cs)
    px = 0.25
    X0, Y0 = math.floor(X0 / px) * px + 0.125, math.floor(Y0 / px) * px + 0.125     # the tiles' own pixel grid (edges at n/4 + 1/8 ft)
    W = int(round((X1 - X0) / px)); H = int(round((Y1 - Y0) / px)); X1 = X0 + W * px; Y1 = Y0 + H * px
    img = np.zeros((H, W, 3), np.uint8); got = np.zeros((H, W), bool); used = []
    for t in tiles:
        url = f'{B}{year}/{t}.tif'
        tw = [float(v) for v in rng(url[:-4] + '.tfw', 0, 300).decode().split()]
        if abs(tw[0] - px) > 1e-9:
            raise SystemExit(f'{t}: pixel {tw[0]} ft, not 0.25')
        tw_, th_, spp, rps, offs = ifd(url)
        tx0 = tw[4] - px / 2; ty1 = tw[5] + px / 2                                   # the tile's outer edges
        c0 = int(round((X0 - tx0) / px)); r0 = int(round((ty1 - Y1) / px))
        a0, a1 = max(0, c0), min(tw_, c0 + W); b0, b1 = max(0, r0), min(th_, r0 + H)
        if a1 <= a0 or b1 <= b0:
            continue
        rows = [offs[r // rps] + (r % rps) * tw_ * spp for r in range(b0, b1)]
        blob = bytearray()
        for i in range(0, len(rows), 128):
            j = min(i + 128, len(rows))
            if rows[j - 1] - rows[i] != (j - 1 - i) * tw_ * spp:
                raise SystemExit(t + ': strips are not contiguous')
            blob += rng(url, rows[i], rows[j - 1] + tw_ * spp - 1)
        part = np.frombuffer(bytes(blob), np.uint8).reshape(b1 - b0, tw_, spp)[:, a0:a1, :3]
        img[b0 - r0:b1 - r0, a0 - c0:a1 - c0] = part; got[b0 - r0:b1 - r0, a0 - c0:a1 - c0] = True
        used.append({'tile': t, 'url': url, 'rows': [b0, b1], 'cols': [a0, a1]})
    Image.fromarray(img).save(out)
    side = {'kind': 'bbox', 'bbox_ftus': [X0, Y0, X1, Y1], 'crs': 'EPSG:2232 (inferred from the tiles\' world files)', 'size': [W, H],
            'pixel_ft': px, 'source': f'DRCOG aerial archive, {B}{year}/', 'tiles': used, 'uncovered_px': int((~got).sum()),
            'frame_box_m_x0_y0_x1_y1': [x0, y0, x1, y1], 'bytes_fetched': FETCHED[0],
            'read_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    json.dump(side, open(os.path.splitext(out)[0] + '.json', 'w'), indent=1)
    print(out, W, 'x', H, 'px;', len(used), 'tiles;', side['uncovered_px'], 'px uncovered;', FETCHED[0] // 1000000, 'MB fetched')


if __name__ == '__main__':
    a = sys.argv
    main(a[1], float(a[2]), float(a[3]), float(a[4]), float(a[5]), a[6], a[a.index('--tiles') + 1].split(','))

"""Stitch Planetary Computer NAIP XYZ tiles over a lon/lat bbox into one PNG + georef JSON.
usage: pc_tiles.py ITEM ZOOM minlon minlat maxlon maxlat OUT.png"""
import io, json, math, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))   # repo root, for scripts.tls when run standalone
from scripts.tls import https_context  # noqa: E402  (TLS verified like every other fetch: tests/net/test_https_everywhere.py)

item, z = sys.argv[1], int(sys.argv[2])
minlon, minlat, maxlon, maxlat = map(float, sys.argv[3:7])
out = sys.argv[7]
URL = ("https://planetarycomputer.microsoft.com/api/data/v1/collections/naip/items/{item}"
       "/tiles/WebMercatorQuad/{z}/{x}/{y}@1x?assets=image&asset_bidx=image%7C1,2,3")

def tx(lon): return (lon + 180) / 360 * 2 ** z
def ty(lat):
    r = math.radians(lat); return (1 - math.log(math.tan(r) + 1 / math.cos(r)) / math.pi) / 2 * 2 ** z

x0, x1 = int(tx(minlon)), int(tx(maxlon)); y0, y1 = int(ty(maxlat)), int(ty(minlat))
img = Image.new("RGB", ((x1 - x0 + 1) * 256, (y1 - y0 + 1) * 256), (255, 0, 255))

def get(xy):
    x, y = xy
    for _ in range(3):
        try:
            with urllib.request.urlopen(URL.format(item=item, z=z, x=x, y=y), timeout=60, context=https_context()) as r:
                return xy, r.read()
        except Exception as e:
            err = e
    return xy, None

xys = [(x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)]
miss = 0
with ThreadPoolExecutor(8) as ex:
    for (x, y), data in ex.map(get, xys):
        if data is None: miss += 1; continue
        img.paste(Image.open(io.BytesIO(data)).convert("RGB"), ((x - x0) * 256, (y - y0) * 256))
img.save(out)
# pixel (px,py) -> tile coords (x0 + px/256, y0 + py/256) at zoom z -> lon/lat (Web Mercator)
json.dump({"item": item, "z": z, "x0": x0, "y0": y0, "w": img.width, "h": img.height,
           "m_per_px_equator": 156543.03392804097 / 2 ** z, "missing_tiles": miss},
          open(out.rsplit(".", 1)[0] + ".georef.json", "w"), indent=1)
print(out, img.size, "tiles", len(xys), "missing", miss)

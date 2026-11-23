"""Stitch Planetary Computer NAIP XYZ tiles over a lon/lat bbox into one image + georef JSON.

usage: pc_tiles.py ITEM[,ITEM...] ZOOM minlon minlat maxlon maxlat OUT.(png|jpg) [--raw DIR] [--quality Q]

ITEM is one STAC item id, or several joined by commas in order of preference (a scene's quarter-quads, say). Each tile
is drawn from the first item whose footprint (the STAC geometry) holds the whole tile. Where none holds it, or its tile
comes back partial (a PNG whose alpha masks the scene's edge), the other items whose bbox touches the tile fill the
masked pixels, in the same order. Pixels no item covers stay magenta (255, 0, 255). With one item it works as it did
before, except that a partial tile's masked pixels are now magenta rather than the black under the alpha.

--raw DIR keeps every tile exactly as served, DIR/<item>/<z>/<x>/<y>.(jpg|png), and each item's STAC JSON,
DIR/<item>.stac.json. A re-run reuses them. --quality Q is the JPEG quality for a .jpg OUT (Pillow's 75 without it).

The georef (OUT minus its extension, + .georef.json) keeps the first version's keys: item (the first of the items), z,
x0, y0, w, h, m_per_px_equator, missing_tiles (tiles no item covers at all). Added: items (in order, each with its
datetime, gsd and the number of tiles it drew pixels into), box, tiles, missing ([x, y] tile addresses at z),
partial_tiles and partial ([x, y, fraction filled]), quality, source.

2026-11-23: the data API's /collections/naip/items/{item}/tiles route answers 404 "Not Found" for every tile now, so
the first version would have stitched an all-magenta image and counted every tile missing. Tiles now come from
/item/tiles with collection= and item= in the query: the URL template in the items' own tilejson asset. A 404 counts
as missing only when the API says the tile "is outside bounds". Any other failure, after retries, stops the run.
"""
import io, json, math, sys, time, urllib.error, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from PIL import Image, ImageChops

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))   # repo root, for scripts.tls when run standalone
from scripts.tls import https_context  # noqa: E402  (TLS verified like every other fetch: tests/net/test_https_everywhere.py)

API = "https://planetarycomputer.microsoft.com/api"
TILE_URL = API + "/data/v1/item/tiles/WebMercatorQuad/{z}/{x}/{y}@1x?{q}"
STAC_URL = API + "/stac/v1/collections/naip/items/{item}"
FILL = (255, 0, 255)
TRIES = 5
SOURCE = ("USDA FSA NAIP (public domain) via the Microsoft Planetary Computer data API: item tiles, WebMercatorQuad "
          "@1x, bands 1,2,3")


class Outside(Exception):
    """The API's 404 for a tile beyond the item's bounds."""


def fetch(url):
    """The body; Outside for the API's 'outside bounds' 404. 429 / 5xx / network errors retry with backoff."""
    last = None
    for k in range(TRIES):
        try:
            with urllib.request.urlopen(url, timeout=60, context=https_context()) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            body = e.read()[:300]
            if e.code == 404 and b"outside bounds" in body:
                raise Outside(url) from None
            if e.code < 500 and e.code != 429:
                raise RuntimeError(f"{url}: HTTP {e.code} {body!r}") from None
            last = f"HTTP {e.code} {body!r}"
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last = repr(e)
        time.sleep(2 + 3 * k)
    raise RuntimeError(f"{url}: {last}")


def inside(ring, lon, lat):
    """Ray casting: is (lon, lat) inside the polygon ring [[lon, lat], ...]?"""
    c = False
    for (xa, ya), (xb, yb) in zip(ring, ring[1:] + ring[:1]):
        if (ya > lat) != (yb > lat) and lon < xa + (lat - ya) * (xb - xa) / (yb - ya):
            c = not c
    return c


def main(argv):
    pos, opt = [], {}
    while argv:
        a = argv.pop(0)
        if a.startswith("--"):
            opt[a] = argv.pop(0)
        else:
            pos.append(a)
    items, z = pos[0].split(","), int(pos[1])
    box = [float(v) for v in pos[2:6]]
    out = pos[6]
    raw = Path(opt["--raw"]) if "--raw" in opt else None
    quality = int(opt["--quality"]) if "--quality" in opt else None
    n = 2 ** z

    def tx(lon): return (lon + 180) / 360 * n
    def ty(lat):
        r = math.radians(lat); return (1 - math.log(math.tan(r) + 1 / math.cos(r)) / math.pi) / 2 * n
    def tlon(x): return x / n * 360 - 180
    def tlat(y): return math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))

    stac = {}
    for it in items:
        p = raw / f"{it}.stac.json" if raw else None
        if p and p.exists():
            body = p.read_bytes()
        else:
            body = fetch(STAC_URL.format(item=it))
            if p:
                p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(body)
        stac[it] = json.loads(body)
        if stac[it].get("id") != it or stac[it]["geometry"]["type"] != "Polygon":
            raise SystemExit(f"{it}: unexpected STAC item ({stac[it].get('id')}, {stac[it]['geometry']['type']})")

    def order(x, y):
        """Items to ask for tile (x, y): those whose footprint holds it, then those whose bbox touches it."""
        W, E, N, S = tlon(x), tlon(x + 1), tlat(y), tlat(y + 1)
        holds, touches = [], []
        for it in items:
            ring = stac[it]["geometry"]["coordinates"][0]
            bw, bs, be, bn = stac[it]["bbox"]
            if all(inside(ring, lo, la) for lo, la in ((W, N), (E, N), (E, S), (W, S))):
                holds.append(it)
            elif W < be and E > bw and S < bn and N > bs:
                touches.append(it)
        return holds + touches

    full = Image.new("L", (256, 256), 255)
    def build(xy):
        x, y = xy
        tile, have = Image.new("RGB", (256, 256), FILL), Image.new("L", (256, 256), 0)
        used, st = [], {"requests": 0, "bytes": 0, "outside": 0, "reused": 0}
        for it in order(x, y):
            here = raw / it / str(z) / str(x) if raw else None
            cached = [here / f"{y}.{e}" for e in ("jpg", "png") if (here / f"{y}.{e}").exists()] if raw else []
            if cached:
                data = cached[0].read_bytes(); st["reused"] += 1
            else:
                st["requests"] += 1
                try:
                    data = fetch(TILE_URL.format(z=z, x=x, y=y, q=urllib.parse.urlencode(
                        {"collection": "naip", "item": it, "assets": "image", "asset_bidx": "image|1,2,3"})))
                except Outside:
                    st["outside"] += 1; continue
                st["bytes"] += len(data)
            im = Image.open(io.BytesIO(data), formats=("JPEG", "PNG")); im.load()
            if im.size != (256, 256):
                raise SystemExit(f"{it} {z}/{x}/{y}: tile {im.size}, not 256x256")
            if raw and not cached:
                here.mkdir(parents=True, exist_ok=True)
                (here / f"{y}.{'png' if im.format == 'PNG' else 'jpg'}").write_bytes(data)
            masked = "A" in im.getbands() or "transparency" in im.info
            a = im.convert("RGBA").getchannel("A").point(lambda v: 255 if v else 0) if masked else full
            m = ImageChops.multiply(a, ImageChops.invert(have))
            if m.getbbox() is None:
                continue
            tile.paste(im.convert("RGB"), (0, 0), m)
            have = ImageChops.lighter(have, a)
            used.append(it)
            if ImageChops.invert(have).getbbox() is None:
                break
        return xy, tile, have.histogram()[255], used, st

    x0, x1 = int(tx(box[0])), int(tx(box[2])); y0, y1 = int(ty(box[3])), int(ty(box[1]))
    img = Image.new("RGB", ((x1 - x0 + 1) * 256, (y1 - y0 + 1) * 256), FILL)
    xys = [(x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)]
    drew = {it: 0 for it in items}
    missing, partial, tot = [], [], {"requests": 0, "bytes": 0, "outside": 0, "reused": 0}
    with ThreadPoolExecutor(8) as ex:
        for k, ((x, y), tile, filled, used, st) in enumerate(ex.map(build, xys), 1):
            img.paste(tile, ((x - x0) * 256, (y - y0) * 256))
            for it in used:
                drew[it] += 1
            for key in tot:
                tot[key] += st[key]
            if filled == 0:
                missing.append([x, y])
            elif filled < 65536:
                partial.append([x, y, round(filled / 65536, 4)])
            if k % 250 == 0 or k == len(xys):
                print(f"[pc_tiles] {k}/{len(xys)} tiles, {tot}", flush=True)
    if quality is not None and out.lower().endswith((".jpg", ".jpeg")):
        img.save(out, quality=quality)
    else:
        img.save(out)
    # pixel (px,py) -> tile coords (x0 + px/256, y0 + py/256) at zoom z -> lon/lat (Web Mercator)
    georef = {"item": items[0], "z": z, "x0": x0, "y0": y0, "w": img.width, "h": img.height,
              "m_per_px_equator": 156543.03392804097 / 2 ** z, "missing_tiles": len(missing),
              "items": [{"id": it, "datetime": stac[it]["properties"].get("datetime"),
                         "gsd": stac[it]["properties"].get("gsd"), "tiles": drew[it]} for it in items],
              "box": box, "tiles": len(xys), "missing": missing, "partial_tiles": len(partial), "partial": partial,
              "quality": quality, "source": SOURCE}
    with open(out.rsplit(".", 1)[0] + ".georef.json", "w") as f:
        json.dump(georef, f, indent=1)
    print(out, img.size, "tiles", len(xys), "missing", len(missing), "partial", len(partial),
          "drew", drew, "fetch", tot)


if __name__ == "__main__":
    main(sys.argv[1:])

"""A NAIP crop at the scene's native resolution, read from Microsoft's Planetary Computer (ledger 0081).

USGS's NAIP ImageServer serves only each state's latest year it holds (Colorado: 2019 at 0.6 m), and the z18 web tiles
undersample a 0.3 m scene (0.46 m at High Plains' latitude). The Planetary Computer carries every NAIP year as the
USDA delivered it (public domain, USDA FSA): Colorado's 2023 flight is 0.3 m. Its data API crops one STAC item to a
lon/lat box, reprojected to EPSG:4326 at exactly the box's corners; this tool asks for it in tiles of at most TILE_PX
pixels a side (the API's own limit) and stitches them, so the image's corners ARE the box (aerial_edges.py --corners).

    python tools/naip_crop.py --item co_m_3910317_ne_13_030_20230928_20240104 --box W,S,E,N --out <png>
                              [--m-per-px 0.3]
    python tools/naip_crop.py --item <id> --track <track-dir> [--margin-m 40] --out <png>   (the box round the
                              track's data/gate_centerline.json, or its source line, plus the margin)

Writes <png> and <png minus .png>.json: {"item", "collection", "datetime", "gsd", "corners": [W, N, E, S], "w", "h",
"m_per_px": [x, y], "source"}. Pixels are square in metres at the box's middle latitude (so NOT square in degrees: the
corners are honoured exactly, which is the property aerial_edges.py relies on). Certificate verification stays ON.
"""
from __future__ import annotations

import io
import json
import math
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.tls import https_context  # noqa: E402  (OS-verified TLS; verification never off)

DATA = "https://planetarycomputer.microsoft.com/api/data/v1/item/bbox/{w},{s},{e},{n}/{px}x{py}.png"
STAC = "https://planetarycomputer.microsoft.com/api/stac/v1/collections/naip/items/{item}"
TILE_PX = 1024          # the data API's largest side we ask for in one request
RETRIES = 4


def mpd(lat0):
    phi = math.radians(lat0)
    return (111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi),
            111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi))


def get(url, timeout=120):
    last = None
    for k in range(RETRIES):
        try:
            with urllib.request.urlopen(url, timeout=timeout, context=https_context()) as r:
                return r.read()
        except Exception as e:      # 5xx / timeouts on a busy API: back off and retry
            last = e
            time.sleep(2 + 3 * k)
    raise RuntimeError(f"{url}: {last}")


def track_box(tdir: Path, margin_m: float):
    # the same frame tools/aerial_edges.py reads: data/centerline.local.json's origin, x = east, the third = north
    local = json.loads((tdir / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    lon0, lat0 = float(local["origin"]["lon"]), float(local["origin"]["lat"])
    pts = json.loads((tdir / "data" / "gate_centerline.json").read_text(encoding="utf-8"))["points_xyz_m"]
    xs = [q[0] for q in pts]
    zs = [q[2] for q in pts]
    mx, my = mpd(lat0)
    return (lon0 + (min(xs) - margin_m) / mx, lat0 + (min(zs) - margin_m) / my,
            lon0 + (max(xs) + margin_m) / mx, lat0 + (max(zs) + margin_m) / my)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    opt = {}
    while argv:
        k = argv.pop(0)
        opt[k] = argv.pop(0)
    item = opt["--item"]
    out = Path(opt["--out"])
    mpp = float(opt.get("--m-per-px", 0.3))
    if "--box" in opt:
        W, S, E, N = (float(v) for v in opt["--box"].split(","))
    else:
        W, S, E, N = track_box(Path(opt["--track"]), float(opt.get("--margin-m", 40)))
    meta = json.loads(get(STAC.format(item=item)))
    mx, my = mpd((S + N) / 2)
    w_px = max(1, round((E - W) * mx / mpp))
    h_px = max(1, round((N - S) * my / mpp))
    nx, ny = math.ceil(w_px / TILE_PX), math.ceil(h_px / TILE_PX)
    canvas = Image.new("RGB", (w_px, h_px))
    for j in range(ny):
        for i in range(nx):
            x0, x1 = i * TILE_PX, min(w_px, (i + 1) * TILE_PX)
            y0, y1 = j * TILE_PX, min(h_px, (j + 1) * TILE_PX)
            tw = W + (E - W) * x0 / w_px
            te = W + (E - W) * x1 / w_px
            tn = N - (N - S) * y0 / h_px
            ts = N - (N - S) * y1 / h_px
            q = urllib.parse.urlencode({"collection": "naip", "item": item, "assets": "image",
                                        "asset_bidx": "image|1,2,3", "nodata": 0})
            url = DATA.format(w=f"{tw:.8f}", s=f"{ts:.8f}", e=f"{te:.8f}", n=f"{tn:.8f}", px=x1 - x0, py=y1 - y0) + "?" + q
            tile = Image.open(io.BytesIO(get(url))).convert("RGB")
            if tile.size != (x1 - x0, y1 - y0):
                raise SystemExit(f"tile {i},{j}: got {tile.size}, asked {(x1 - x0, y1 - y0)}")
            canvas.paste(tile, (x0, y0))
            print(f"[naip_crop] tile {j * nx + i + 1}/{nx * ny}", flush=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out)
    p = meta.get("properties", {})
    rec = {"item": item, "collection": "naip", "datetime": p.get("datetime"), "gsd": p.get("gsd"),
           "corners": [W, N, E, S], "w": w_px, "h": h_px,
           "m_per_px": [round((E - W) * mx / w_px, 4), round((N - S) * my / h_px, 4)],
           "source": "Microsoft Planetary Computer data API (USDA FSA NAIP, public domain), EPSG:4326 crop"}
    out.with_suffix(".json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print(f"[naip_crop] {out} {w_px}x{h_px} px, {rec['m_per_px']} m/px, {item} ({rec['datetime']}, gsd {rec['gsd']})")


if __name__ == "__main__":
    main()

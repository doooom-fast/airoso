"""Phase 3 Step 0 aerial: NAIP 2022-04-25 windows over the three western roads, west to -117.11.

The windows are tools/naip_carriageways.py's Mosaic tiles (its request shape and cache format): 600 m squares on
the fixed grid of Lake Murray's engine frame (data/centerline.local.json origin, x east / z north), tile (i, j)
covering x in [600 i, 600 (i + 1)), z in [600 j, 600 (j + 1)); each read from Microsoft's Planetary Computer data
API as a 1000 x 1000 px .npy crop (0.6 m), bands R G B NIR (asset_bidx image|1,2,3,4, nodata 0) of the STAC item
whose footprint holds the tile centre 0.002 deg inside (Mosaic._item), stored as naip_{i}_{j}.npy (4, 1000, 1000)
uint8 - the file Mosaic(cache=DIR) reads without fetching.

The box: the roads' extent (p3_west.py's planned pavement) + 150 m [invented], west edge at -117.11 (the brief).

    python -I p3_naip.py <expansion.west.planned.json> <out-dir> <cap-bytes> <log.jsonl> [--plan-only]
"""
import hashlib
import io
import json
import math
import sys
import time
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import p3_net  # noqa: E402

TILE_M, MPP = 600.0, 0.6
PX = int(round(TILE_M / MPP))
STAC = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
DATA = "https://planetarycomputer.microsoft.com/api/data/v1/item/bbox/{w},{s},{e},{n}/{px}x{py}.npy"
WEST_LON = -117.11
MARGIN_M = 150.0
DATE = "2022-04-25"


def mpd(lat0):
    phi = math.radians(lat0)
    return (111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi),
            111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi))


def main():
    import numpy as np
    west, out, cap, log = json.load(open(sys.argv[1])), Path(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    plan_only = "--plan-only" in sys.argv
    out.mkdir(parents=True, exist_ok=True)
    o = west["frame"]["origin"]
    lon0, lat0 = o["lon"], o["lat"]
    mx, my = mpd(lat0)
    ll = lambda x, z: (lon0 + x / mx, lat0 + z / my)
    ex = west["extent"]
    x0 = (WEST_LON - lon0) * mx
    x1 = ex["x"][1] + MARGIN_M
    z0, z1 = ex["z"][0] - MARGIN_M, ex["z"][1] + MARGIN_M
    I = range(math.floor(x0 / TILE_M), math.floor(x1 / TILE_M) + 1)
    Jr = range(math.floor(z0 / TILE_M), math.floor(z1 / TILE_M) + 1)
    budget = p3_net.Budget(cap, log)
    W, S = ll(I[0] * TILE_M, Jr[0] * TILE_M)
    E, N = ll((I[-1] + 1) * TILE_M, (Jr[-1] + 1) * TILE_M)
    q = {"collections": ["naip"], "bbox": [W, S, E, N], "datetime": f"{DATE}T00:00:00Z/{DATE}T23:59:59Z", "limit": 50}
    raw = p3_net.request(STAC, json.dumps(q).encode(), budget, {"Content-Type": "application/json"})
    feats = json.loads(raw.decode()).get("features", [])
    items = sorted([(f["id"], f["bbox"], f["properties"].get("datetime"), f["properties"].get("gsd")) for f in feats])
    print("items", [(i[0], i[1]) for i in items], flush=True)
    tiles = []
    for j in Jr:
        for i in I:
            tw, ts_ = ll(i * TILE_M, j * TILE_M)
            te, tn = ll((i + 1) * TILE_M, (j + 1) * TILE_M)
            cl, ca = (tw + te) / 2, (ts_ + tn) / 2
            it = next((it for it in items if it[1][0] + 0.002 <= cl <= it[1][2] - 0.002
                       and it[1][1] + 0.002 <= ca <= it[1][3] - 0.002), None)
            tiles.append({"i": i, "j": j, "bbox_wsen": [tw, ts_, te, tn], "item": it[0] if it else None})
    plan = {"what": "NAIP 2022-04-25 windows, Mosaic tiles (tools/naip_carriageways.py)", "origin": o,
            "tile_m": TILE_M, "px": PX, "box_engine": [x0, z0, x1, z1], "west_lon": WEST_LON, "margin_m": MARGIN_M,
            "items": [{"id": a, "bbox": b, "datetime": c, "gsd": d} for a, b, c, d in items], "tiles": tiles}
    (out / "PLAN.json").write_text(json.dumps(plan, indent=1))
    print(f"{len(tiles)} tiles, i {I[0]}..{I[-1]}, j {Jr[0]}..{Jr[-1]}; no item: "
          f"{[(t['i'], t['j']) for t in tiles if not t['item']]}", flush=True)
    if plan_only:
        return
    src = []
    for n, t in enumerate(tiles):
        f = out / f"naip_{t['i']}_{t['j']}.npy"
        if f.exists() or not t["item"]:
            continue
        w, s, e, nn = t["bbox_wsen"]
        qs = urllib.parse.urlencode({"collection": "naip", "item": t["item"], "assets": "image",
                                     "asset_bidx": "image|1,2,3,4", "nodata": 0})
        url = DATA.format(w=f"{w:.8f}", s=f"{s:.8f}", e=f"{e:.8f}", n=f"{nn:.8f}", px=PX, py=PX) + "?" + qs
        body = p3_net.request(url, None, budget, {"Accept": "*/*"})
        arr = np.load(io.BytesIO(body), allow_pickle=False)
        if arr.dtype != np.uint8 or arr.ndim != 3 or arr.shape[1:] != (PX, PX) or arr.shape[0] < 4:
            raise SystemExit(f"tile {t['i']},{t['j']}: unexpected array {arr.dtype} {arr.shape}")
        np.save(f, arr[:4])
        cover = float((arr[:4].max(axis=0) > 0).mean())
        rec = {**t, "url": url, "wire_bytes": len(body), "shape_served": list(arr.shape),
               "md5": hashlib.md5(f.read_bytes()).hexdigest(), "nonzero_share": round(cover, 4),
               "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        src.append(rec)
        print(f"[naip] {n + 1}/{len(tiles)} {f.name} {t['item']} {len(body)} B cover {cover:.3f}; total {budget.used} B",
              flush=True)
        time.sleep(1.0)
    prev = json.loads((out / "SOURCE.json").read_text())["tiles"] if (out / "SOURCE.json").exists() else []
    allsrc = prev + src
    (out / "SOURCE.json").write_text(json.dumps({"source": "Microsoft Planetary Computer data API (USDA FSA NAIP, public "
                                                           "domain), EPSG:4326 crop at the tile's corners",
                                                 "user_agent": p3_net.UA, "tiles": allsrc,
                                                 "bytes": budget.used, "requests": budget.requests}, indent=1))
    (out / "MANIFEST.md5").write_text("".join(f"{r['md5']}  naip_{r['i']}_{r['j']}.npy\n" for r in allsrc))
    print("done", budget.requests, "requests", budget.used, "B", flush=True)


if __name__ == "__main__":
    main()

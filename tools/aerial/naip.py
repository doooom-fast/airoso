"""Small georeferenced NAIP windows from The National Map's ImageServer, cached on disk.

Each window is requested twice from ``exportImage``: true colour (bands 0,1,2) and colour infrared
(bands 3,0,1, NIR first), in EPSG:26913 (NAD83 / UTM 13N, the Colorado NAIP quarter-quads' own
projection, so the server does not reproject), PNG, bilinear, at the service's own 0.3 m pixel (the
source is 0.6 m). The bbox IS the georeference: pixel (i, j)'s centre is
``(xmin + (i + 0.5) * px, ymax - (j + 0.5) * px)``. Nothing is pinned by hand.

**TLS verification is always on**: every request goes through ``scripts.tls.https_context()`` (the OS
verifier via truststore; urllib's own verifying default where truststore is absent). Never pass an
unverified context here.

The cache holds ``<id>.json`` (bbox, size, the exact request URLs, the catalog rasters, fetch time) next
to ``<id>_rgb.png`` / ``<id>_cir.png``. A cached window is reused only when its bbox and size match the
request exactly. Public-domain imagery (US federal work): credit "USGS, USDA, The National Map:
Orthoimagery".

No thresholds here; the retry count and back-off are transport settings.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.tls import https_context  # noqa: E402  (verification on, never disabled)

from . import geo  # noqa: E402

SERVICE = "https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPImagery/ImageServer"
EPSG = 26913
UA = {"User-Agent": "airoso-aerial-measure/1.0 (public-domain NAIP measurement; small windows)"}


def default_cache() -> Path:
    """Where raw windows live when ``--cache`` is not given: never in the repo."""
    env = os.environ.get("AIROSO_NAIP_CACHE")
    if env:
        return Path(env)
    base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".cache")
    return Path(base) / "airoso" / "naip"


def _get(url: str, tries: int = 8):
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, context=https_context(), timeout=120) as r:
                return r.read(), r.headers.get("Content-Type", "")
        except Exception as e:  # the service answers 502 now and then: back off and retry
            last = e
            time.sleep(3 + 5 * k)
    raise last


def bbox_for(E0: float, N0: float, half_w: float, half_h: float | None = None, px: float = 0.3):
    """The exact bbox and pixel size a window centred on (E0, N0) is requested with."""
    half_h = half_w if half_h is None else half_h
    xmin, xmax = round(E0 - half_w, 2), round(E0 + half_w, 2)
    ymin, ymax = round(N0 - half_h, 2), round(N0 + half_h, 2)
    W = int(round((xmax - xmin) / px))
    H = int(round((ymax - ymin) / px))
    xmax = round(xmin + W * px, 2)
    ymax = round(ymin + H * px, 2)
    return [xmin, ymin, xmax, ymax], [W, H]


def window(cache: Path, wid: str, E0: float, N0: float, half_w: float, half_h: float | None = None,
           px: float = 0.3, fetch: bool = True) -> dict:
    """Window ``wid`` centred on imagery-frame (E0, N0): reused from ``cache`` when its bbox and size
    match, else fetched (TLS verified) when ``fetch`` is true. Returns its metadata dict."""
    cache = Path(cache)
    bbox, size = bbox_for(E0, N0, half_w, half_h, px)
    meta_p = cache / f"{wid}.json"
    if meta_p.exists():
        m = json.loads(meta_p.read_text(encoding="utf-8"))
        if m["bbox_utm13n"] == bbox and m["size"] == size and _files_present(cache, wid):
            m["_cache"] = str(cache)
            return m
    if not fetch:
        raise SystemExit(f"[aerial] window {wid} is not in the cache {cache} (bbox {bbox}); "
                         "run with fetching allowed")
    cache.mkdir(parents=True, exist_ok=True)
    xmin, ymin, xmax, ymax = bbox
    W, H = size
    base = {
        "bbox": f"{xmin},{ymin},{xmax},{ymax}", "bboxSR": EPSG, "imageSR": EPSG,
        "size": f"{W},{H}", "format": "png", "pixelType": "U8",
        "interpolation": "RSP_BilinearInterpolation", "noData": "", "f": "image",
    }
    files = {}
    for name, bands in (("rgb", "0,1,2"), ("cir", "3,0,1")):
        q = dict(base, bandIds=bands)
        url = SERVICE + "/exportImage?" + urllib.parse.urlencode(q)
        data, ctype = _get(url)
        if not ctype.startswith("image/"):
            raise RuntimeError(f"{wid} {name}: not an image ({ctype}): {data[:300]!r}")
        p = cache / f"{wid}_{name}.png"
        p.write_bytes(data)
        files[name] = {"path": p.name, "url": url, "bytes": len(data)}
    lon, lat = geo.from_utm(E0, N0)
    qurl = SERVICE + "/query?" + urllib.parse.urlencode({
        "where": "Category=1", "geometry": f"{lon},{lat}", "geometryType": "esriGeometryPoint",
        "inSR": 4326, "spatialRel": "esriSpatialRelIntersects",
        "outFields": "Name,Year,State,acquisition_date,resolution_value,projection_zone,datum,vendor",
        "returnGeometry": "false", "f": "json"})
    try:
        cat = json.loads(_get(qurl)[0].decode("utf-8"))
        rasters = [f["attributes"] for f in cat.get("features", [])]
    except Exception as e:  # provenance only; the pixels are already fetched
        rasters = [{"error": str(e)}]
    m = {"id": wid, "bbox_utm13n": bbox, "crs": f"EPSG:{EPSG} (NAD83 / UTM 13N)",
         "size": size, "px_m": px, "centre_lonlat": [round(lon, 7), round(lat, 7)],
         "files": files, "catalog": rasters,
         "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    meta_p.write_text(json.dumps(m, indent=1), encoding="utf-8", newline="\n")
    m["_cache"] = str(cache)
    return m


def _files_present(cache: Path, wid: str) -> bool:
    return (cache / f"{wid}_rgb.png").exists() and (cache / f"{wid}_cir.png").exists()


def px_of(m, E, N):
    """Imagery-frame (E, N) -> fractional pixel (x, y), pixel-centre convention."""
    xmin, ymin, xmax, ymax = m["bbox_utm13n"]
    px = m["px_m"]
    return (E - xmin) / px - 0.5, (ymax - N) / px - 0.5


def utm_of(m, x, y):
    xmin, ymin, xmax, ymax = m["bbox_utm13n"]
    px = m["px_m"]
    return xmin + (x + 0.5) * px, ymax - (y + 0.5) * px


class Win:
    """Pixel access for a cached window: bilinear R, G, B, NIR at imagery-frame coordinates."""

    def __init__(self, meta: dict):
        from PIL import Image
        self.m = meta
        cache = Path(meta["_cache"])
        wid = meta["id"]
        self.rgb_path = cache / f"{wid}_rgb.png"
        self.cir_path = cache / f"{wid}_cir.png"
        rgb = Image.open(self.rgb_path).convert("RGB")
        cir = Image.open(self.cir_path).convert("RGB")
        self.W, self.H = rgb.size
        self.rgb = rgb.load()
        self.cir = cir.load()
        self.rgb_img = rgb

    def px(self, E, N):
        return px_of(self.m, E, N)

    def sample(self, E, N):
        x, y = self.px(E, N)
        if x < 0 or y < 0 or x > self.W - 1.001 or y > self.H - 1.001:
            return None
        x0, y0 = int(x), int(y)
        fx, fy = x - x0, y - y0
        out = [0.0, 0.0, 0.0, 0.0]
        for (xx, yy, w) in ((x0, y0, (1 - fx) * (1 - fy)), (x0 + 1, y0, fx * (1 - fy)),
                            (x0, y0 + 1, (1 - fx) * fy), (x0 + 1, y0 + 1, fx * fy)):
            r, g, b = self.rgb[xx, yy]
            nir = self.cir[xx, yy][0]
            out[0] += w * r
            out[1] += w * g
            out[2] += w * b
            out[3] += w * nir
        return out

"""An orthophoto, its georeference read from its own metadata, and the local ENU frame every measurement is made in.

Georeference kinds (``Ortho.load``); the CRS always comes from the file or its sidecar, never a constant:

  geotiff   a GeoTIFF's ModelTiepoint / ModelPixelScale tags and its GeoKey EPSG (projected or geographic), read with
            Pillow; any EPSG through pyproj, or without pyproj EPSG:4326 and the UTM zones on NAD83 / WGS84 (269zz, 326zz,
            327zz) by the Krueger series (tools/aerial/geo.py's, the zone a parameter here);
  corners   a crop sidecar ``{"corners": [W, N, E, S], "w", "h"}`` (tools/naip_crop.py: Planetary Computer crops,
            EPSG:4326, the image's corners ARE the box; the sketch page writes ``corners_wnes`` the same way);
  bbox      a projected window sidecar ``{"bbox_*": [xmin, ymin, xmax, ymax], "crs": "EPSG:n ...", "size"}``
            (tools/aerial/naip.py's windows);
  tiles     a Web Mercator tile stitch ``{"z", "x0", "y0"}`` (pc_tiles.py, Exotics);
  control_points  two ``{px, lonlat}`` corners in scripts/aerial/build_aerial.py's convention (px = continuous image
            coordinates, (0, 0) the top-left corner of the top-left pixel).

Pixel convention in this package: pixel (i, j)'s CENTRE is (i, j) (``x`` right, ``y`` down); continuous corner
coordinates are pixel + 0.5.

The local frame: ENU metres about ``origin`` (lon, lat) by scripts/geometry/projection's metres-per-degree series, the
frame data/centerline.local.json uses. Pixel <-> ENU is the exact transform evaluated on a 21 x 21 grid and fitted with a
cubic polynomial each way; the fit's worst residual over the image is reported (``fit_px``) and must be under
FIT_TOL_PX, else the stage stops.

Registration (register.py) moves the image: ENU_true = ENU_image - shift. ``set_shift`` applies it to every conversion.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

FIT_TOL_PX = 0.01          # a polynomial fit worse than this over the image is refused (numerical, not a judgement)


def mpd(lat0: float) -> tuple[float, float]:
    """Metres per degree (lon, lat) at lat0: scripts/geometry/projection._meters_per_degree's series."""
    phi = math.radians(lat0)
    m_lat = 111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
    m_lon = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi)
    return m_lon, m_lat


# --- UTM by the Krueger n-series (3 terms), any zone, GRS80 or WGS84 -------------------------------------------------

def _tm_consts(f):
    n = f / (2 - f)
    A = 6378137.0 / (1 + n) * (1 + n ** 2 / 4 + n ** 4 / 64)
    alpha = [n / 2 - 2 * n ** 2 / 3 + 5 * n ** 3 / 16, 13 * n ** 2 / 48 - 3 * n ** 3 / 5, 61 * n ** 3 / 240]
    beta = [n / 2 - 2 * n ** 2 / 3 + 37 * n ** 3 / 96, n ** 2 / 48 + n ** 3 / 15, 17 * n ** 3 / 480]
    delta = [2 * n - 2 * n ** 2 / 3 - 2 * n ** 3, 7 * n ** 2 / 3 - 8 * n ** 3 / 5, 56 * n ** 3 / 15]
    return A, alpha, beta, delta


def utm_inverse(E, N, zone: int, south: bool = False, f: float = 1 / 298.257222101):
    """(E, N) metres -> (lon, lat) degrees, UTM ``zone`` (vectorised)."""
    A, _, beta, delta = _tm_consts(f)
    k0 = 0.9996
    E = np.asarray(E, float)
    N = np.asarray(N, float) - (10000000.0 if south else 0.0)
    xi = N / (k0 * A)
    eta = (E - 500000.0) / (k0 * A)
    xi_p = xi - sum(beta[j] * np.sin(2 * (j + 1) * xi) * np.cosh(2 * (j + 1) * eta) for j in range(3))
    eta_p = eta - sum(beta[j] * np.cos(2 * (j + 1) * xi) * np.sinh(2 * (j + 1) * eta) for j in range(3))
    chi = np.arcsin(np.sin(xi_p) / np.cosh(eta_p))
    phi = chi + sum(delta[j] * np.sin(2 * (j + 1) * chi) for j in range(3))
    lam = np.arctan2(np.sinh(eta_p), np.cos(xi_p))
    return np.degrees(lam) + (zone * 6 - 183), np.degrees(phi)


def _epsg_to_lonlat(epsg: int):
    """A vectorised (x, y) -> (lon, lat) for the EPSG code: pyproj when installed, else 4326 / UTM built in."""
    try:
        from pyproj import Transformer
        t = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)
        return lambda x, y: t.transform(np.asarray(x, float), np.asarray(y, float)), "pyproj"
    except Exception:  # pragma: no cover - exercised only where pyproj is absent
        pass
    if epsg == 4326 or epsg == 4269:
        return (lambda x, y: (np.asarray(x, float), np.asarray(y, float))), "identity"
    if 26901 <= epsg <= 26923:
        return (lambda x, y: utm_inverse(x, y, epsg - 26900)), "krueger NAD83"
    if 32601 <= epsg <= 32660:
        return (lambda x, y: utm_inverse(x, y, epsg - 32600, f=1 / 298.257223563)), "krueger WGS84"
    if 32701 <= epsg <= 32760:
        return (lambda x, y: utm_inverse(x, y, epsg - 32700, south=True, f=1 / 298.257223563)), "krueger WGS84 S"
    raise SystemExit(f"[aerial-engine] EPSG:{epsg} needs pyproj (not installed); only 4326 / 4269 / UTM are built in")


def _geotiff_tags(path: Path):
    """(tiepoint, scale, epsg, raster_is_point) from a GeoTIFF's tags (Pillow)."""
    im = Image.open(path)
    tags = getattr(im, "tag_v2", None)
    if tags is None or 33922 not in tags or 33550 not in tags:
        raise SystemExit(f"[aerial-engine] {path}: no ModelTiepoint / ModelPixelScale tags (not a GeoTIFF)")
    tie = [float(v) for v in tags[33922]]
    scale = [float(v) for v in tags[33550]]
    keys = [int(v) for v in tags.get(34735, ())]
    epsg, is_point = None, False
    for k in range(4, len(keys), 4):
        kid, loc, _cnt, val = keys[k:k + 4]
        if loc != 0:
            continue
        if kid in (3072, 2048) and val not in (0, 32767):
            epsg = epsg if (kid == 2048 and epsg) else val
        if kid == 1025:             # GTRasterTypeGeoKey: 1 area, 2 point
            is_point = val == 2
    if epsg is None:
        raise SystemExit(f"[aerial-engine] {path}: the GeoKey directory names no EPSG code")
    return tie, scale, epsg, is_point


class Ortho:
    """An RGB orthophoto with an exact georeference and a local ENU frame."""

    def __init__(self, rgb: np.ndarray, px_to_lonlat, desc: dict, origin=None):
        self.rgb = rgb.astype(np.float32)
        self.H, self.W = rgb.shape[:2]
        self._exact = px_to_lonlat                     # (x, y) pixel-centre coords -> (lon, lat), vectorised
        self.desc = desc
        lon_c, lat_c = px_to_lonlat(np.array([(self.W - 1) / 2]), np.array([(self.H - 1) / 2]))
        self.set_origin(origin if origin is not None else (float(lon_c[0]), float(lat_c[0])))
        self.shift = np.zeros(2)

    # -- construction --------------------------------------------------------------------------------------------
    @classmethod
    def load(cls, image, georef: dict | None = None, origin=None) -> "Ortho":
        """``georef``: None (a GeoTIFF's tags, else ``<image minus suffix>.json`` beside it), a path to a sidecar
        json, or a dict of one of the kinds in the module docstring."""
        path = Path(image)
        rgb = np.asarray(Image.open(path).convert("RGB"))
        H, W = rgb.shape[:2]
        meta = georef
        if isinstance(meta, (str, Path)):
            meta = json.loads(Path(meta).read_text(encoding="utf-8"))
        if meta is None:
            if path.suffix.lower() in (".tif", ".tiff"):
                meta = {"kind": "geotiff"}
            else:
                side = path.with_suffix(".json")
                if not side.exists():
                    raise SystemExit(f"[aerial-engine] {path}: no georeference (no GeoTIFF tags, no {side.name})")
                meta = json.loads(side.read_text(encoding="utf-8"))
        f, desc = cls._georef(path, meta, W, H)
        desc["image"] = str(path)
        desc["size_px"] = [W, H]
        return cls(rgb, f, desc, origin)

    @staticmethod
    def _georef(path: Path, meta: dict, W: int, H: int):
        kind = meta.get("kind")
        if kind is None:
            if "corners" in meta or "corners_wnes" in meta:
                kind = "corners"
            elif "z" in meta and "x0" in meta:
                kind = "tiles"
            elif "control_points" in meta:
                kind = "control_points"
            elif any(k.startswith("bbox") for k in meta) and "crs" in meta:
                kind = "bbox"
        if kind == "geotiff":
            tie, scale, epsg, is_point = _geotiff_tags(path)
            to_ll, how = _epsg_to_lonlat(epsg)
            I, J, _, X, Y, _ = tie[:6]
            sx, sy = scale[0], scale[1]
            off = 0.0 if is_point else 0.5              # area rasters: the tiepoint is the pixel's corner

            def f(x, y):
                return to_ll(X + (np.asarray(x, float) - I + off) * sx, Y - (np.asarray(y, float) - J + off) * sy)
            return f, {"kind": "geotiff", "crs": f"EPSG:{epsg}", "transform": how, "px_size": [sx, sy]}
        if kind == "corners":
            c = meta.get("corners") or meta.get("corners_wnes")
            w_, n_, e_, s_ = (float(v) for v in c)
            w0 = float(meta.get("w") or meta.get("image_w") or W)
            h0 = float(meta.get("h") or meta.get("image_h") or H)
            if (int(w0), int(h0)) != (W, H):
                raise SystemExit(f"[aerial-engine] {path}: sidecar says {int(w0)} x {int(h0)} px, image is {W} x {H}")

            def f(x, y):
                return (w_ + (np.asarray(x, float) + 0.5) / W * (e_ - w_),
                        n_ - (np.asarray(y, float) + 0.5) / H * (n_ - s_))
            return f, {"kind": "corners", "crs": "EPSG:4326 (the crop's corners)", "corners_wnes": [w_, n_, e_, s_]}
        if kind == "bbox":
            bkey = next(k for k in meta if k.startswith("bbox"))
            xmin, ymin, xmax, ymax = (float(v) for v in meta[bkey])
            epsg = int(str(meta["crs"]).split(":")[1].split()[0])
            to_ll, how = _epsg_to_lonlat(epsg)

            def f(x, y):
                return to_ll(xmin + (np.asarray(x, float) + 0.5) * (xmax - xmin) / W,
                             ymax - (np.asarray(y, float) + 0.5) * (ymax - ymin) / H)
            return f, {"kind": "bbox", "crs": f"EPSG:{epsg}", "transform": how}
        if kind == "tiles":
            z, x0, y0 = int(meta["z"]), float(meta["x0"]), float(meta["y0"])
            n = 2.0 ** z

            def f(x, y):
                X = x0 + (np.asarray(x, float) + 0.5) / 256.0
                Y = y0 + (np.asarray(y, float) + 0.5) / 256.0
                return X / n * 360.0 - 180.0, np.degrees(np.arctan(np.sinh(np.pi * (1 - 2 * Y / n))))
            return f, {"kind": "tiles", "crs": f"EPSG:3857 tiles z{z} from tile ({int(x0)}, {int(y0)})"}
        if kind == "control_points":
            (p1, l1), (p2, l2) = [((float(c["px"][0]), float(c["px"][1])), (float(c["lonlat"][0]), float(c["lonlat"][1])))
                                  for c in meta["control_points"][:2]]
            p1 = (p1[0] * W, p1[1] * H) if max(abs(p1[0]), abs(p1[1])) <= 1.5 else p1
            p2 = (p2[0] * W, p2[1] * H) if max(abs(p2[0]), abs(p2[1])) <= 1.5 else p2
            sx = (l2[0] - l1[0]) / (p2[0] - p1[0])
            sy = (l2[1] - l1[1]) / (p2[1] - p1[1])

            def f(x, y):
                return l1[0] + (np.asarray(x, float) + 0.5 - p1[0]) * sx, l1[1] + (np.asarray(y, float) + 0.5 - p1[1]) * sy
            return f, {"kind": "control_points", "crs": "EPSG:4326 north-up affine from two corner pins"}
        raise SystemExit(f"[aerial-engine] {path}: unknown georeference {sorted(meta)}")

    # -- frames ----------------------------------------------------------------------------------------------------
    def set_origin(self, origin):
        self.origin = (float(origin[0]), float(origin[1]))
        self.m_lon, self.m_lat = mpd(self.origin[1])
        gx, gy = np.meshgrid(np.linspace(0, self.W - 1, 21), np.linspace(0, self.H - 1, 21))
        lon, lat = self._exact(gx.ravel(), gy.ravel())
        e = (np.asarray(lon) - self.origin[0]) * self.m_lon
        n = (np.asarray(lat) - self.origin[1]) * self.m_lat
        self._fwd = _polyfit(gx.ravel(), gy.ravel(), e, n)          # px -> enu
        self._inv = _polyfit(e, n, gx.ravel(), gy.ravel())          # enu -> px
        # the fit's worst residual, checked on an offset grid (not the fitting nodes)
        tx, ty = np.meshgrid(np.linspace(0.5, self.W - 1.5, 17), np.linspace(0.5, self.H - 1.5, 17))
        lo, la = self._exact(tx.ravel(), ty.ravel())
        te = (np.asarray(lo) - self.origin[0]) * self.m_lon
        tn = (np.asarray(la) - self.origin[1]) * self.m_lat
        bx, by = _polyval(self._inv, te, tn)
        self.fit_px = float(np.max(np.hypot(bx - tx.ravel(), by - ty.ravel())))
        if self.fit_px > FIT_TOL_PX:
            raise SystemExit(f"[aerial-engine] the image -> ENU polynomial misses by {self.fit_px:.4f} px (> {FIT_TOL_PX})")
        ex, ey = _polyval(self._fwd, np.array([0.0, 1.0, 0.0]), np.array([0.0, 0.0, 1.0]))
        self.gsd = (float(np.hypot(ex[1] - ex[0], ey[1] - ey[0])), float(np.hypot(ex[2] - ex[0], ey[2] - ey[0])))

    def set_shift(self, shift_en):
        self.shift = np.asarray(shift_en, float).reshape(2)

    def px_to_en(self, x, y):
        """pixel-centre coords -> TRUE ENU (the registration shift removed)."""
        e, n = _polyval(self._fwd, np.asarray(x, float), np.asarray(y, float))
        return e - self.shift[0], n - self.shift[1]

    def en_to_px(self, e, n):
        """TRUE ENU -> pixel-centre coords (the image is displaced by ``shift``)."""
        return _polyval(self._inv, np.asarray(e, float) + self.shift[0], np.asarray(n, float) + self.shift[1])

    def en_to_px_raw(self, e, n):
        """Image-frame ENU (no registration) -> pixel; for measuring the registration itself."""
        return _polyval(self._inv, np.asarray(e, float), np.asarray(n, float))

    def en_to_lonlat(self, e, n):
        return (self.origin[0] + np.asarray(e, float) / self.m_lon, self.origin[1] + np.asarray(n, float) / self.m_lat)

    def lonlat_to_en(self, lon, lat):
        return ((np.asarray(lon, float) - self.origin[0]) * self.m_lon, (np.asarray(lat, float) - self.origin[1]) * self.m_lat)

    def px_to_lonlat(self, x, y):
        return self.en_to_lonlat(*self.px_to_en(x, y))

    def describe(self) -> dict:
        return {**self.desc, "origin_lonlat": [round(self.origin[0], 8), round(self.origin[1], 8)],
                "gsd_m": [round(self.gsd[0], 4), round(self.gsd[1], 4)], "frame_fit_max_px": round(self.fit_px, 6),
                "registration_shift_en_m": [round(float(v), 3) for v in self.shift]}


def _terms(x, y):
    return np.stack([np.ones_like(x), x, y, x * x, x * y, y * y, x ** 3, x * x * y, x * y * y, y ** 3], axis=-1)


def _polyfit(x, y, u, v):
    """Cubic u(x, y), v(x, y) by least squares on centred, scaled inputs."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    c = (x.mean(), y.mean(), max(np.ptp(x), 1e-9), max(np.ptp(y), 1e-9))
    A = _terms((x - c[0]) / c[2], (y - c[1]) / c[3])
    cu = np.linalg.lstsq(A, np.asarray(u, float), rcond=None)[0]
    cv = np.linalg.lstsq(A, np.asarray(v, float), rcond=None)[0]
    return c, cu, cv


def _polyval(fit, x, y):
    c, cu, cv = fit
    x = np.asarray(x, float); y = np.asarray(y, float)
    T = _terms((x - c[0]) / c[2], (y - c[1]) / c[3])
    return T @ cu, T @ cv

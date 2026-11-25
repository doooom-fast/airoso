"""COLORADO BLVD'S LIGHT POLES READ ON A 3-INCH ORTHOPHOTO (DRAPP 2022), the second source after the 2020 lidar
(colorado_poles_g10.py). Data only: nothing reads it. The photo itself stays out of git (CC0 on the public bucket,
CC BY 3.0 in DRCOG's own metadata: either way it is kept local, as asked).

THE PHOTO: the Denver Regional Aerial Photography Project's 2022 orthophoto (DRCOG), 3-inch (0.25 ft) 4-band (R, G, B,
NIR) uncompressed GeoTIFF tiles, 2640 ft square, NAD83(2011) / Colorado Central (US ft, EPSG:6428), on the State of Colorado's
public bucket (s3://colorado-public-imagery/DRAPP/DRAPP2022/, read anonymously over HTTPS). `fetch` reads only the crop:
each tile's TIFF directory, then the crop's pixel runs by HTTP range (every ROW_STEP-th row: 7.62 cm across x, 15.24 cm
along y), into one north-up array (crop.npz: rgbn, the state plane origin and steps) and a viewing PNG.

THE CROP: the lap's Colorado stations s CROP_S, u CROP_U (the lap's frame: centerline.local.json, +u = left of travel,
west here), as its state plane bounding box.

THE READING (`chips`, then `poles`): a pole counts as READ only when its head or arm and its shadow line agree on its
base. `chips` writes north-up views of the crop with a metre grid in the lap's s / u; the reader marks, per pole, the
base (where the shadow line and the pole / arm image meet) and the head, in crop pixels, with what agrees, in a picks
file; `poles` turns the picks into s / u / lon / lat, the side and distance from the measured curbs (CURBS_U), the
built lamps' nearest read pole, and the photo's shadow azimuth (the mean of the picks' base-to-shadow-tip bearings).

    python -I colorado_ortho_g10.py fetch --repo R --out DIR
    python -I colorado_ortho_g10.py chips --repo R --crop DIR/crop.npz --out DIR/chips
    python -I colorado_ortho_g10.py poles --repo R --crop DIR/crop.npz --picks picks.json --out JSON
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import math
import ssl
import struct
import sys
import time
from pathlib import Path

# The repo's TLS rule (scripts/tls.py, tests/net/test_https_everywhere.py): every fetch uses scripts.tls.https_context().
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from scripts.tls import https_context  # noqa: E402

HOST = "colorado-public-imagery.s3.us-west-2.amazonaws.com"
PREFIX = "DRAPP/DRAPP2022"
CRS = 6428                    # NAD83(2011) / Colorado Central (ftUS): each tile's GeoTIFF ProjectedCSTypeGeoKey (the crop's
                              # bounding box was cut with EPSG:2232, the same zone on NAD83(1986): ~1 m apart at most,
                              # inside its 3 ft margin)
PIX_FT = 0.25                 # the tiles' pixel (3 inch)
TILE_FT = 2640.0
BLOCK_TOP_N1 = 1747832.0      # the N1 block's top edge (N1E100a.tfw: 1747831.8749 is its first pixel's centre)
BLOCK_LEFT_E1 = 3141392.0     # the E1 block's left edge (N1E100a.tfw: 3141392.1248)
ROW_STEP = 2                  # [sampling] every 2nd row: 15.24 cm along y, the crop's transfer halved
CROP_S = (-20.0, 435.0)       # the task's
CROP_U = (-50.0, 50.0)        # the task's
MARGIN_FT = 3.0               # [sampling]
CURBS_U = {"near_right_curb": -5.25, "median": [5.75, 10.0], "far_curb": 21.0}   # the task's (measured, roads file)
LAMP_NEAR_M = 15.0            # the task's
CURB_TOL_M = 1.5              # [invented] a base this close inside a curb line is read as at that curb: the reading's
                              # +-0.15 m, the curb's own spread along the road, the frames' datum (up to ~1 m)


def mpd(lat0):
    phi = math.radians(lat0)
    return (111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi),
            111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi))


class Lap:
    def __init__(self, repo: Path):
        import numpy as np
        cl = json.loads((repo / "tracks/sand-creek-lm/data/centerline.local.json").read_text())
        self.origin = cl["origin"]
        P = np.asarray(cl["points_xyz_m"], float)
        self.xz = P[:, [0, 2]]
        self.s = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(self.xz, axis=0).T))])
        self.L = float(self.s[-1])

    def at(self, s):
        import numpy as np
        s = np.mod(np.asarray(s, float), self.L)
        return np.stack([np.interp(s, self.s, self.xz[:, 0]), np.interp(s, self.s, self.xz[:, 1])], -1)

    def frame(self, s, h=5.0):
        import numpy as np
        c = self.at(s)
        t = self.at(np.asarray(s) + h) - self.at(np.asarray(s) - h)
        t = t / np.linalg.norm(t, axis=-1, keepdims=True)
        return c, t, np.stack([-t[..., 1], t[..., 0]], -1)

    def su(self, x, z):
        import numpy as np
        from scipy.spatial import cKDTree
        S = np.arange(CROP_S[0] - 60.0, CROP_S[1] + 60.0, 0.1)
        c, t, n = self.frame(S)
        _, k = cKDTree(c).query(np.stack([np.atleast_1d(x), np.atleast_1d(z)], 1))
        dx, dz = np.atleast_1d(x) - c[k, 0], np.atleast_1d(z) - c[k, 1]
        return S[k] + dx * t[k, 0] + dz * t[k, 1], dx * n[k, 0] + dz * n[k, 1]


class Frames:
    """the lap's frame (x, z metres) <-> lon / lat <-> state plane (ft)"""

    def __init__(self, origin):
        from pyproj import Transformer
        self.o = origin
        self.m_lon, self.m_lat = mpd(origin["lat"])
        self.to_sp = Transformer.from_crs(4326, CRS, always_xy=True)
        self.to_ll = Transformer.from_crs(CRS, 4326, always_xy=True)

    def xz_to_ll(self, x, z):
        return self.o["lon"] + x / self.m_lon, self.o["lat"] + z / self.m_lat

    def ll_to_xz(self, lon, lat):
        return (lon - self.o["lon"]) * self.m_lon, (lat - self.o["lat"]) * self.m_lat

    def xz_to_sp(self, x, z):
        return self.to_sp.transform(*self.xz_to_ll(x, z))

    def sp_to_xz(self, X, Y):
        return self.ll_to_xz(*self.to_ll.transform(X, Y))


# ------------------------------------------------------------------------------------------------- the range reader


class S3:
    """anonymous HTTPS GETs on one kept-alive connection, TLS verified; Range reads checked for length"""

    def __init__(self):
        self.ctx = None  # contexts come from scripts.tls at each call
        self.c = None
        self.requests = 0
        self.bytes = 0

    def _conn(self):
        if self.c is None:
            self.c = http.client.HTTPSConnection(HOST, timeout=60, context=https_context())
        return self.c

    def get(self, key, start=None, end=None):
        path = f"/{key}"
        hdr = {"User-Agent": "airoso-ortho/1.0"}
        if start is not None:
            hdr["Range"] = f"bytes={start}-{end}"
        last = None
        for k in range(6):
            try:
                c = self._conn()
                c.request("GET", path, headers=hdr)
                r = c.getresponse()
                body = r.read()
                if r.status not in (200, 206):
                    raise IOError(f"HTTP {r.status} on {key}")
                if start is not None and len(body) != end - start + 1:
                    raise IOError(f"short range {len(body)} of {end - start + 1}")
                self.requests += 1
                self.bytes += len(body)
                return body, dict(r.getheaders())
            except (OSError, http.client.HTTPException) as e:
                last = e
                try:
                    self.c.close()
                except Exception:
                    pass
                self.c = None
                time.sleep(min(30.0, 1.0 * 2 ** k))
        raise SystemExit(f"gave up on {key}: {last}")


TIFF_TYPES = {1: ("B", 1), 2: ("s", 1), 3: ("H", 2), 4: ("I", 4), 5: ("II", 8), 7: ("B", 1), 12: ("d", 8),
              16: ("Q", 8)}


def read_ifd(s3: S3, key):
    """the first IFD of a classic little-endian TIFF: {tag: values}, reading only its bytes and its arrays"""
    head, _ = s3.get(key, 0, 7)
    if head[:4] != b"II*\x00":
        raise SystemExit(f"{key}: not a classic little-endian TIFF")
    off = struct.unpack("<I", head[4:8])[0]
    cnt_b, _ = s3.get(key, off, off + 1)
    n = struct.unpack("<H", cnt_b)[0]
    ent, _ = s3.get(key, off + 2, off + 2 + 12 * n - 1)
    tags = {}
    for i in range(n):
        tag, typ, cnt = struct.unpack("<HHI", ent[12 * i:12 * i + 8])
        raw = ent[12 * i + 8:12 * i + 12]
        fmt, size = TIFF_TYPES.get(typ, ("B", 1))
        nbytes = size * cnt
        if nbytes > 4:
            vo = struct.unpack("<I", raw)[0]
            raw, _ = s3.get(key, vo, vo + nbytes - 1)
        if typ == 2:
            tags[tag] = raw[:nbytes].split(b"\x00")[0].decode("ascii", "replace")
        elif typ == 5:
            v = struct.unpack("<" + "I" * (2 * cnt), raw[:nbytes])
            tags[tag] = [v[2 * j] / v[2 * j + 1] for j in range(cnt)]
        else:
            tags[tag] = list(struct.unpack("<" + fmt * cnt, raw[:nbytes]))
    return tags


def tile_name(X, Y):
    """the DRAPP 2022 tile holding state plane (X, Y): N1E1{row}{col}{quadrant} inside the N1 / E1 10-mile block"""
    col = int((X - BLOCK_LEFT_E1) // 5280.0)
    row = int((BLOCK_TOP_N1 - Y) // 5280.0)
    if not (0 <= col <= 9 and 0 <= row <= 9):
        raise SystemExit("the crop is outside the N1 / E1 block this reader knows")
    x0 = BLOCK_LEFT_E1 + col * 5280.0
    y0 = BLOCK_TOP_N1 - row * 5280.0
    east = X - x0 >= TILE_FT
    south = y0 - Y > TILE_FT
    q = {(False, False): "a", (True, False): "b", (False, True): "c", (True, True): "d"}[(east, south)]
    return f"N1E1{row}{col}{q}", (x0 + (TILE_FT if east else 0.0), y0 - (TILE_FT if south else 0.0))


def cmd_fetch(a):
    import numpy as np
    repo = Path(a.repo).resolve()
    lap = Lap(repo)
    fr = Frames(lap.origin)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    S = np.linspace(CROP_S[0], CROP_S[1], 92)
    c, t, n = lap.frame(S)
    pts = np.concatenate([c + n * CROP_U[0], c + n * CROP_U[1]])
    X, Y = fr.xz_to_sp(pts[:, 0], pts[:, 1])
    X0, X1 = float(np.min(X)) - MARGIN_FT, float(np.max(X)) + MARGIN_FT
    Y0, Y1 = float(np.min(Y)) - MARGIN_FT, float(np.max(Y)) + MARGIN_FT
    # the crop's pixel grid is the tiles' own: column edges every PIX_FT from BLOCK_LEFT_E1, rows every PIX_FT from
    # BLOCK_TOP_N1, of which every ROW_STEP-th (even rows of the block grid)
    gc0 = int(math.floor((X0 - BLOCK_LEFT_E1) / PIX_FT))
    gc1 = int(math.ceil((X1 - BLOCK_LEFT_E1) / PIX_FT))
    gr0 = int(math.floor((BLOCK_TOP_N1 - Y1) / PIX_FT))
    gr1 = int(math.ceil((BLOCK_TOP_N1 - Y0) / PIX_FT))
    gr0 -= gr0 % ROW_STEP
    rows = list(range(gr0, gr1, ROW_STEP))
    W = gc1 - gc0
    s3 = S3()
    img = None
    tiles = {}
    corners = [(X0, Y0), (X0, Y1), (X1, Y0), (X1, Y1)]
    names = {}
    for Xc, Yc in corners:
        nm, (tx0, ty0) = tile_name(Xc, Yc)
        names[nm] = (tx0, ty0)
    for nm, (tx0, ty0) in sorted(names.items()):
        key = f"{PREFIX}/{nm}.tif"
        tfw, _ = s3.get(f"{PREFIX}/{nm}.tfw")
        v = [float(x) for x in tfw.decode().split()]
        if abs(v[0] - PIX_FT) > 1e-6 or abs(v[4] - (tx0 + PIX_FT / 2)) > 1e-3 or abs(v[5] - (ty0 - PIX_FT / 2)) > 1e-3:
            raise SystemExit(f"{nm}.tfw {v} is not the grid this reader assumes ({tx0}, {ty0})")
        tags = read_ifd(s3, key)
        w, h = tags[256][0], tags[257][0]
        spp, bps, comp = tags[277][0], tags[258], tags[259][0]
        planar = tags.get(284, [1])[0]
        if comp != 1 or set(bps) != {8} or planar != 1:
            raise SystemExit(f"{nm}: compression {comp}, bits {bps}, planar {planar}: not the uncompressed chunky "
                             f"8-bit layout this reader reads")
        geok = tags.get(34735, [])
        proj = None
        for j in range(4, len(geok), 4):
            if geok[j] == 3072:
                proj = geok[j + 3]
        rps = tags.get(278, [h])[0]
        offs = tags[273]
        _, hdrs = s3.get(key, 0, 0)
        tiles[nm] = {"key": key, "width": w, "height": h, "spp": spp, "rows_per_strip": rps,
                     "projected_crs": proj, "datetime": tags.get(306), "software": tags.get(305),
                     "etag": hdrs.get("ETag", "").strip('"'), "last_modified": hdrs.get("Last-Modified"),
                     "origin_ft": [tx0, ty0]}
        if img is None:
            img = np.zeros((len(rows), W, spp), np.uint8)
        # this tile's columns and rows inside the crop
        tc0 = int(round((tx0 - BLOCK_LEFT_E1) / PIX_FT))
        tr0 = int(round((BLOCK_TOP_N1 - ty0) / PIX_FT))
        c0, c1 = max(gc0, tc0), min(gc1, tc0 + w)
        if c1 <= c0:
            continue
        for i, gr in enumerate(rows):
            r = gr - tr0
            if not (0 <= r < h):
                continue
            strip, within = divmod(r, rps)
            start = offs[strip] + (within * w + (c0 - tc0)) * spp
            end = start + (c1 - c0) * spp - 1
            body, _ = s3.get(key, start, end)
            img[i, c0 - gc0:c1 - gc0, :] = np.frombuffer(body, np.uint8).reshape(c1 - c0, spp)
        print(f"[ortho] {nm}: cols {c0 - tc0}..{c1 - tc0}, requests so far {s3.requests}, bytes {s3.bytes:,}",
              flush=True)
    meta = {"source": f"https://{HOST}/{PREFIX}/", "tiles": tiles, "crs": f"EPSG:{CRS}",
            "origin_ft": [BLOCK_LEFT_E1 + gc0 * PIX_FT, BLOCK_TOP_N1 - rows[0] * PIX_FT],
            "step_ft": [PIX_FT, -PIX_FT * ROW_STEP], "shape": list(img.shape),
            "crop_s": list(CROP_S), "crop_u": list(CROP_U), "requests": s3.requests, "bytes_read": s3.bytes}
    np.savez_compressed(out / "crop.npz", rgbn=img, origin_ft=np.array(meta["origin_ft"]),
                        step_ft=np.array(meta["step_ft"]))
    from PIL import Image
    Image.fromarray(img[:, :, :3]).save(out / "crop_rgb.png")
    for f in ("crop.npz", "crop_rgb.png"):
        meta[f"md5_{f}"] = hashlib.md5((out / f).read_bytes()).hexdigest()
    (out / "crop.json").write_text(json.dumps(meta, indent=1))
    print(f"[ortho] crop {img.shape}, {s3.requests} requests, {s3.bytes:,} bytes", flush=True)
    return 0


def load_crop(p):
    import numpy as np
    d = np.load(p)
    return d["rgbn"], d["origin_ft"], d["step_ft"]


def px_to_xz(fr, origin, step, col, row):
    """crop pixel centre (col, row) -> the lap's frame (x, z)"""
    X = origin[0] + (col + 0.5) * step[0]
    Y = origin[1] + (row + 0.5) * step[1]
    return fr.sp_to_xz(X, Y)


def xz_to_px(fr, origin, step, x, z):
    import numpy as np
    X, Y = fr.xz_to_sp(np.asarray(x, float), np.asarray(z, float))
    return (X - origin[0]) / step[0] - 0.5, (Y - origin[1]) / step[1] - 0.5


def cmd_chips(a):
    """north-up views, CHIP_M of s each (overlapping 5 m), pixels squared (rows doubled), with an s / u grid every 5 m
    (s ticks along the left edge, u = 0, +-5.25, +5.75, +10, +21 drawn) and a pixel ruler; the built lamps ringed"""
    import numpy as np
    from PIL import Image, ImageDraw
    repo = Path(a.repo).resolve()
    lap = Lap(repo)
    fr = Frames(lap.origin)
    img, origin, step = load_crop(a.crop)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    lights = json.loads((repo / "tracks/sand-creek-lm/data/lights.local.json").read_text())
    LB = np.asarray(lights["lamp_bases_xz"], float)
    chip_m = float(a.chip_m)
    k = 0
    s = CROP_S[0]
    while s < CROP_S[1]:
        s1 = min(s + chip_m, CROP_S[1])
        cs, _, ns = lap.frame(np.array([s, s1]))
        pa = [cs[0] + ns[0] * CROP_U[0], cs[0] + ns[0] * CROP_U[1], cs[1] + ns[1] * CROP_U[0], cs[1] + ns[1] * CROP_U[1]]
        cols, rows = xz_to_px(fr, origin, step, [p[0] for p in pa], [p[1] for p in pa])
        r0, r1 = int(max(0, np.floor(min(rows)))), int(min(img.shape[0], np.ceil(max(rows))))
        sub = img[r0:r1, :, :3]
        im = Image.fromarray(np.repeat(sub, ROW_STEP, axis=0))
        d = ImageDraw.Draw(im)

        def P(x, z):
            cc, rr = xz_to_px(fr, origin, step, x, z)
            return float(cc), float((rr - r0) * ROW_STEP)
        for sg in np.arange(math.ceil(s / 5.0) * 5.0, s1 + 1e-6, 5.0):
            c1, t1, n1 = lap.frame(np.array([sg]))
            a1 = P(*(c1[0] + n1[0] * CROP_U[0])); b1 = P(*(c1[0] + n1[0] * CROP_U[1]))
            d.line([a1, b1], fill=(255, 255, 0) if sg % 25 == 0 else (90, 90, 0), width=1)
            d.text((b1[0] + 2, b1[1] - 6), f"s{sg:.0f}", fill=(255, 255, 0))
        SS = np.linspace(s, s1, 30)
        cc, _, nn = lap.frame(SS)
        for uu, col in ((0.0, (0, 255, 255)), (-5.25, (255, 0, 255)), (5.75, (255, 0, 255)), (10.0, (255, 0, 255)),
                        (21.0, (255, 0, 255)), (-11.05, (255, 128, 0)), (11.05, (255, 128, 0))):
            q = [P(*(cc[j] + nn[j] * uu)) for j in range(len(SS))]
            d.line(q, fill=col, width=1)
        for i, (x, z) in enumerate(LB):
            sl, ul = lap.su(x, z)
            if s - 2 <= sl[0] <= s1 + 2 and abs(ul[0]) < 50:
                px, py = P(x, z)
                d.ellipse([px - 12, py - 12, px + 12, py + 12], outline=(255, 64, 64), width=2)
                d.text((px + 14, py), f"lamp{i}", fill=(255, 64, 64))
        for xg in range(0, im.size[0], 100):
            d.line([(xg, 0), (xg, 8)], fill=(255, 255, 255))
            d.text((xg + 1, 9), str(xg), fill=(255, 255, 255))
        for yg in range(0, im.size[1], 100):
            d.line([(0, yg), (8, yg)], fill=(255, 255, 255))
            d.text((10, yg + 1), str(yg // ROW_STEP + r0), fill=(255, 255, 255))
        im.save(out / f"chip_{k:02d}_s{s:.0f}_{s1:.0f}.png")
        k += 1
        s = s1 - 5.0 if s1 < CROP_S[1] else s1
    print(f"[ortho] {k} chips -> {out}", flush=True)
    return 0


def cmd_crop(a):
    """one zoomed view: crop pixels (col0, row0, col1, row1), scaled, rows doubled; a pixel grid every 20 px"""
    import numpy as np
    from PIL import Image, ImageDraw
    img, origin, step = load_crop(a.crop)
    c0, r0, c1, r1 = [int(v) for v in a.box.split(",")]
    sub = np.repeat(img[r0:r1, c0:c1, :3], ROW_STEP, axis=0)
    sc = int(a.scale)
    im = Image.fromarray(sub).resize((sub.shape[1] * sc, sub.shape[0] * sc), Image.NEAREST)
    d = ImageDraw.Draw(im)
    for xg in range((c0 // 20 + 1) * 20, c1, 20):
        X = (xg - c0) * sc
        d.line([(X, 0), (X, 6)], fill=(255, 255, 0))
        d.text((X + 1, 7), str(xg), fill=(255, 255, 0))
    for yg in range((r0 // 10 + 1) * 10, r1, 10):
        Y = (yg - r0) * ROW_STEP * sc
        d.line([(0, Y), (6, Y)], fill=(255, 255, 0))
        d.text((8, Y + 1), str(yg), fill=(255, 255, 0))
    im.save(a.out)
    return 0


def cmd_poles(a):
    """the picks (crop pixels) -> the read poles: base s / u / lon / lat, side and distance from the curbs, the shadow
    (length, azimuth), each arm read off its shadow (junction -> head shadow: length, bearing, toward the road or
    not), and the built lamps' nearest read pole"""
    import numpy as np
    repo = Path(a.repo).resolve()
    lap = Lap(repo)
    fr = Frames(lap.origin)
    img, origin, step = load_crop(a.crop)
    picks = json.loads(Path(a.picks).read_text())

    def xz(pt):
        return px_to_xz(fr, origin, step, pt[0], pt[1])

    def bearing(p0, p1):
        return (math.degrees(math.atan2(p1[0] - p0[0], p1[1] - p0[1])) + 360.0) % 360.0

    poles = []
    az = []
    for p in picks["poles"]:
        bx, bz = xz(p["base_px"])
        s_b, u_b = lap.su(bx, bz)
        s_b, u_b = float(s_b[0]), float(u_b[0])
        lon, lat = fr.xz_to_ll(bx, bz)
        read = bool(p.get("head_or_arm")) and bool(p.get("shadow"))
        rec = {"id": p["id"], "read": read, "s": round(s_b, 1), "u": round(u_b, 2),
               "base_xz": [round(bx, 2), round(bz, 2)], "base_lonlat": [round(lon, 7), round(lat, 7)],
               "base_px": p["base_px"], "evidence": {"head_or_arm": p.get("head_or_arm"), "shadow": p.get("shadow"),
                                                    "note": p.get("note")}}
        if p.get("shadow_tip_px"):
            tx, tz = xz(p["shadow_tip_px"])
            rec["shadow"] = {"length_m": round(math.hypot(tx - bx, tz - bz), 2),
                             "azimuth_deg": round(bearing((bx, bz), (tx, tz)), 1)}
            az.append(rec["shadow"]["azimuth_deg"])
        arms = []
        if p.get("arm_junction_px") and p.get("head_shadow_px"):
            jx, jz = xz(p["arm_junction_px"])
            _, _, nn = lap.frame(np.array([s_b]))
            for hp in p["head_shadow_px"]:
                hx, hz = xz(hp)
                v = np.array([hx - jx, hz - jz])
                du = float(v @ nn[0])
                if u_b <= CURBS_U["near_right_curb"] + CURB_TOL_M:
                    toward = du > 0
                elif u_b >= CURBS_U["far_curb"] - CURB_TOL_M:
                    toward = du < 0
                else:
                    toward = None                        # in the median: each arm reaches one carriageway
                arms.append({"length_m": round(float(np.hypot(*v)), 2), "bearing_deg": round(bearing((jx, jz), (hx, hz)), 1),
                             "points": "+u (west)" if du > 0 else "-u (east)", "toward_road": toward,
                             "from": "its shadow (the arm's shadow is the arm moved along the sun's ray)"})
        rec["arms"] = arms
        d_near = CURBS_U["near_right_curb"] - u_b          # + = behind (east of) the near curb
        d_far = u_b - CURBS_U["far_curb"]                    # + = behind (west of) the far curb
        if d_near >= -CURB_TOL_M:
            rec["side"] = "east"
            rec["from_curb"] = (f"{d_near:.2f} m behind the near carriageway's curb (u -5.25)" if d_near >= 0 else
                                f"at the near carriageway's curb ({-d_near:.2f} m inside it: the reading's tolerance)")
        elif d_far >= -CURB_TOL_M:
            rec["side"] = "west"
            rec["from_curb"] = (f"{d_far:.2f} m behind the far curb (about u +21)" if d_far >= 0 else
                                f"at the far curb ({-d_far:.2f} m inside its u +21: the reading's tolerance)")
        elif CURBS_U["median"][0] <= u_b <= CURBS_U["median"][1]:
            rec["side"] = "median"
            rec["from_curb"] = (f"{u_b - CURBS_U['median'][0]:.2f} m from its east face, "
                                f"{CURBS_U['median'][1] - u_b:.2f} m from its west face")
        else:
            rec["side"] = "in a carriageway"
            rec["from_curb"] = f"u {u_b:+.2f}"
        poles.append(rec)
    poles.sort(key=lambda r: r["s"])
    read = [p for p in poles if p["read"]]
    lights = json.loads((repo / "tracks/sand-creek-lm/data/lights.local.json").read_text())
    LB = np.asarray(lights["lamp_bases_xz"], float)
    lamps = []
    for i, (x, z) in enumerate(LB):
        sl, ul = lap.su(x, z)
        if not (0.0 <= sl[0] <= 415.0 and abs(ul[0]) <= 30.0):
            continue
        rec = {"lamp": i, "base_xz": [float(x), float(z)], "s": round(float(sl[0]), 1), "u": round(float(ul[0]), 2)}
        if read:
            d = [math.hypot(p["base_xz"][0] - x, p["base_xz"][1] - z) for p in read]
            j = int(np.argmin(d))
            rec.update({"nearest_read_pole": read[j]["id"], "pole_s": read[j]["s"], "pole_u": read[j]["u"],
                        "distance_m": round(d[j], 2),
                        "verdict": (f"{read[j]['id']} at {d[j]:.1f} m" if d[j] <= LAMP_NEAR_M
                                    else f"no read pole within {LAMP_NEAR_M:.0f} m")})
        else:
            rec["verdict"] = f"no read pole within {LAMP_NEAR_M:.0f} m"
        lamps.append(rec)
    others = []
    for o in picks.get("other_objects", []):
        rec = dict(o)
        if o.get("px"):
            ox, oz = xz(o["px"])
            so, uo = lap.su(ox, oz)
            rec.update({"s": round(float(so[0]), 1), "u": round(float(uo[0]), 2), "xz": [round(ox, 2), round(oz, 2)],
                        "lonlat": [round(v, 7) for v in fr.xz_to_ll(ox, oz)]})
        others.append(rec)
    meta = json.loads(Path(a.crop).with_name("crop.json").read_text())
    out = {"_doc": picks.get("_doc"),
           "photo": {"source": meta["source"], "crs": f"EPSG:{CRS}", "crop_box_cut_with": meta["crs"],
                     "pixel_ft": meta["step_ft"],
                     "tiles": {k: {kk: v[kk] for kk in ("key", "etag", "datetime", "last_modified", "projected_crs")}
                               for k, v in meta["tiles"].items()},
                     "crop_shape": meta["shape"], "crop_bytes_read": meta["bytes_read"],
                     "crop_requests": meta["requests"],
                     "crop_md5": {k[4:]: meta[k] for k in meta if k.startswith("md5_")}},
           "shadow_azimuth_deg_median": round(float(np.median(az)), 1) if az else None,
           "curbs_u": CURBS_U, "poles": poles, "lamps": lamps, "other_objects": others,
           "notes": picks.get("notes", [])}
    Path(a.out).write_text(json.dumps(out, indent=1))
    for p in poles:
        print(p["id"], "READ" if p["read"] else "----", p["s"], p["u"], p["side"], p["from_curb"],
              p.get("shadow"), [(x["length_m"], x["points"], x["toward_road"]) for x in p["arms"]])
    for r in lamps:
        print("lamp", r["lamp"], r["s"], r["u"], r["verdict"])
    for o in others:
        print("other", o.get("id"), o.get("s"), o.get("u"), o.get("what"))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("fetch"); p.add_argument("--repo", required=True); p.add_argument("--out", required=True)
    p = sub.add_parser("chips"); p.add_argument("--repo", required=True); p.add_argument("--crop", required=True)
    p.add_argument("--out", required=True); p.add_argument("--chip-m", default="60")
    p = sub.add_parser("crop"); p.add_argument("--crop", required=True); p.add_argument("--box", required=True)
    p.add_argument("--scale", default="2"); p.add_argument("--out", required=True)
    p = sub.add_parser("poles"); p.add_argument("--repo", required=True); p.add_argument("--crop", required=True)
    p.add_argument("--picks", required=True); p.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    return {"fetch": cmd_fetch, "chips": cmd_chips, "crop": cmd_crop, "poles": cmd_poles}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())

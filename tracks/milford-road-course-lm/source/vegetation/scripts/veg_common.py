"""Shared readers for the vegetation pass (ledger 0082): the local frame, the NAIP 2022 frame, the built OBJ's surfaces."""
import json, math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
VEG = HERE.parent                                   # tracks/milford-road-course-lm/source/vegetation
TRACK = VEG.parents[1]                              # tracks/milford-road-course-lm
AIROSO = TRACK.parents[1]
NAIP = AIROSO / "tracks" / "milford-road-course" / "source" / "naip_2022_mrc.jpg"
NAIP_BBOX = (-83.67, 42.56050328638498, -83.657, 42.57949671361502)    # W S E N, ledger 0062's true extent
CELL = 2.0                                          # the inventory grid, m


def mpd(lat0):
    phi = math.radians(lat0)
    return (111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi),
            111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi))


class Frame:
    def __init__(self, origin):
        self.o = origin
        self.m_lon, self.m_lat = mpd(origin["lat"])

    def to_local(self, lon, lat):
        return (np.asarray(lon) - self.o["lon"]) * self.m_lon, (np.asarray(lat) - self.o["lat"]) * self.m_lat

    def to_lonlat(self, e, n):
        return self.o["lon"] + np.asarray(e) / self.m_lon, self.o["lat"] + np.asarray(n) / self.m_lat


def naip_on_grid(frame, e_c, n_c):
    """NAIP 2022 RGB sampled (nearest) at the cell centres e_c (nx,), n_c (ny,); NaN outside the image"""
    from PIL import Image
    im = Image.open(NAIP).convert("RGB")
    a = np.asarray(im).astype(np.float32)
    W, S, E, N = NAIP_BBOX
    ee, nn = np.meshgrid(e_c, n_c)
    lon, lat = frame.to_lonlat(ee, nn)
    px = (lon - W) / (E - W) * im.width
    py = (N - lat) / (N - S) * im.height
    ok = (px >= 0) & (px < im.width) & (py >= 0) & (py < im.height)
    out = np.full(ee.shape + (3,), np.nan, np.float32)
    out[ok] = a[py[ok].astype(int), px[ok].astype(int)]
    return out


def naip_features(frame, E0, N0, nx, ny, cell, sub=4):
    """NAIP 2022 per grid cell, from sub x sub samples inside it (0.5 m at a 2 m cell: the image's own 0.50 x 0.68 m):
    mean R, G, B and the spread (std) of the brightness inside the cell — a crown is rough, a mown field smooth.
    NaN outside the image"""
    from PIL import Image
    im = Image.open(NAIP).convert("RGB")
    a = np.asarray(im).astype(np.float32)
    W, S, E, N = NAIP_BBOX
    e_w, n_s = frame.to_local(W, S)
    e_e, n_n = frame.to_local(E, N)
    i0, i1 = max(0, int((e_w - E0) / cell)), min(nx, int((e_e - E0) / cell) + 1)
    j0, j1 = max(0, int((n_s - N0) / cell)), min(ny, int((n_n - N0) / cell) + 1)
    es = E0 + i0 * cell + (np.arange((i1 - i0) * sub) + 0.5) * cell / sub
    ns = N0 + j0 * cell + (np.arange((j1 - j0) * sub) + 0.5) * cell / sub
    ee, nn = np.meshgrid(es, ns)
    lon, lat = frame.to_lonlat(ee, nn)
    px = (lon - W) / (E - W) * im.width
    py = (N - lat) / (N - S) * im.height
    ok = (px >= 0) & (px < im.width) & (py >= 0) & (py < im.height)
    s = np.full(ee.shape + (3,), np.nan, np.float32)
    s[ok] = a[py[ok].astype(int), px[ok].astype(int)]
    hh, ww = (j1 - j0), (i1 - i0)
    blk = s.reshape(hh, sub, ww, sub, 3)
    rgb = np.full((ny, nx, 3), np.nan, np.float32)
    sd = np.full((ny, nx), np.nan, np.float32)
    with np.errstate(invalid="ignore"):
        rgb[j0:j1, i0:i1] = np.nanmean(blk, axis=(1, 3)) if np.isfinite(blk).any() else np.nan
        sd[j0:j1, i0:i1] = np.nanstd(blk.mean(axis=4), axis=(1, 3))
    return rgb, sd


def obj_surfaces(obj_path, prefixes):
    """{prefix: [triangles (3, 2) in local (e, n)]} for the gate OBJ's objects / materials whose name starts with a prefix
    (the gate OBJ is the engine frame: x = E, z = N)"""
    V, out, cur = [], {p: [] for p in prefixes}, None
    with open(obj_path, encoding="utf-8", errors="replace") as f:
        for ln in f:
            c = ln[:2]
            if c == "v ":
                p = ln.split()
                V.append((float(p[1]), float(p[3])))
            elif ln.startswith("usemtl ") or c in ("o ", "g "):
                nm = ln.split(None, 1)[1].strip().upper()
                cur = next((p for p in prefixes if nm.startswith(p)), None)
            elif c == "f " and cur is not None:
                idx = [int(q.split("/")[0]) - 1 for q in ln.split()[1:]]
                for i in range(1, len(idx) - 1):
                    out[cur].append((V[idx[0]], V[idx[i]], V[idx[i + 1]]))
    return {k: np.array(v, np.float64).reshape(-1, 3, 2) for k, v in out.items()}


def raster_tris(tris, E0, N0, nx, ny, cell, wall_w=0.0):
    """mark the cells whose centre lies in a triangle; a triangle with no plan area (a wall) marks the cells its edges
    pass within wall_w of"""
    m = np.zeros((ny, nx), bool)
    for t in tris:
        (ax, az), (bx, bz), (cx, cz) = t
        area = (bx - ax) * (cz - az) - (cx - ax) * (bz - az)
        x0, x1 = min(ax, bx, cx) - wall_w, max(ax, bx, cx) + wall_w
        z0, z1 = min(az, bz, cz) - wall_w, max(az, bz, cz) + wall_w
        i0, i1 = max(0, int((x0 - E0) / cell)), min(nx - 1, int((x1 - E0) / cell))
        j0, j1 = max(0, int((z0 - N0) / cell)), min(ny - 1, int((z1 - N0) / cell))
        if i1 < i0 or j1 < j0:
            continue
        xs = E0 + (np.arange(i0, i1 + 1) + 0.5) * cell
        zs = N0 + (np.arange(j0, j1 + 1) + 0.5) * cell
        X, Z = np.meshgrid(xs, zs)
        if abs(area) > 1e-6:
            d1 = (bx - ax) * (Z - az) - (X - ax) * (bz - az)
            d2 = (cx - bx) * (Z - bz) - (X - bx) * (cz - bz)
            d3 = (ax - cx) * (Z - cz) - (X - cx) * (az - cz)
            inside = ~(((d1 < 0) | (d2 < 0) | (d3 < 0)) & ((d1 > 0) | (d2 > 0) | (d3 > 0)))
        else:
            inside = np.zeros_like(X, bool)
            for (px, pz), (qx, qz) in (((ax, az), (bx, bz)), ((bx, bz), (cx, cz))):
                dx, dz = qx - px, qz - pz
                L2 = dx * dx + dz * dz
                tt = np.clip(((X - px) * dx + (Z - pz) * dz) / L2, 0, 1) if L2 > 0 else 0 * X
                inside |= np.hypot(X - (px + tt * dx), Z - (pz + tt * dz)) <= max(wall_w, cell * 0.71)
        m[j0:j1 + 1, i0:i1 + 1] |= inside
    return m

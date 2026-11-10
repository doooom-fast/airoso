"""Height above ground for every point of an extract (ledger 0089): ground = the lowest class-2 return per GRID_M cell,
gaps filled by nearest, bilinear at each point. Coordinates out in TRUE metres east / north of the box's SW corner."""
import math
import numpy as np
from scipy import ndimage as ndi
R = 6378137.0
GRID_M = 1.0
def load(npz, lat0):
    d = np.load(npz)
    k = math.cos(math.radians(lat0))                 # EPSG:3857 metres are 1/cos(lat) true metres
    x0, y0 = d["x"].min(), d["y"].min()
    X, Y = (d["x"] - x0) * k, (d["y"] - y0) * k
    Z, C = d["z"], d["c"]
    nx, ny = int(X.max() / GRID_M) + 2, int(Y.max() / GRID_M) + 2
    g = np.full((ny, nx), np.inf)
    gm = C == 2
    ix, iy = (X[gm] / GRID_M).astype(int), (Y[gm] / GRID_M).astype(int)
    np.minimum.at(g, (iy, ix), Z[gm])
    miss = ~np.isfinite(g)
    idx = ndi.distance_transform_edt(miss, return_distances=False, return_indices=True)
    g = g[tuple(idx)]
    fx, fy = X / GRID_M - 0.5, Y / GRID_M - 0.5
    i0, j0 = np.clip(np.floor(fx).astype(int), 0, nx - 2), np.clip(np.floor(fy).astype(int), 0, ny - 2)
    tx, ty = np.clip(fx - i0, 0, 1), np.clip(fy - j0, 0, 1)
    G = (g[j0, i0] * (1 - tx) * (1 - ty) + g[j0, i0 + 1] * tx * (1 - ty) + g[j0 + 1, i0] * (1 - tx) * ty + g[j0 + 1, i0 + 1] * tx * ty)
    def to_xy(lon, lat):
        return ((math.radians(lon) * R - x0) * k, (R * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)) - y0) * k)
    def to_lonlat(x, y):
        return (math.degrees((x / k + x0) / R), math.degrees(2 * math.atan(math.exp((y / k + y0) / R)) - math.pi / 2))
    return {"X": X, "Y": Y, "Z": Z, "C": C, "HAG": Z - G, "ground": g, "to_xy": to_xy, "to_lonlat": to_lonlat}

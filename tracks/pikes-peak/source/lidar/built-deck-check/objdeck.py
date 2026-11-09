"""Height queries on a built gate OBJ (engine frame: x = E, y = up, z = N)."""
import numpy as np
from collections import defaultdict


def load_obj(path, want=lambda name: True):
    V = []; faces = defaultdict(list); cur = None
    with open(path) as f:
        for line in f:
            if line.startswith("v "):
                V.append([float(t) for t in line.split()[1:4]])
            elif line.startswith("o "):
                cur = line[2:].strip()
            elif line.startswith("f ") and want(cur):
                idx = [int(t.split("/")[0]) - 1 for t in line.split()[1:]]
                for k in range(1, len(idx) - 1):
                    faces[cur].append((idx[0], idx[k], idx[k + 1]))
    return np.array(V), {k: np.array(v) for k, v in faces.items()}


class Surface:
    def __init__(self, V, F, cell=4.0):
        self.V, self.F, self.cell = V, F, cell
        tri = V[F]
        self.tri = tri
        mn = tri[:, :, [0, 2]].min(1); mx = tri[:, :, [0, 2]].max(1)
        self.grid = defaultdict(list)
        for t, (a, b) in enumerate(zip(mn, mx)):
            for i in range(int(np.floor(a[0] / cell)), int(np.floor(b[0] / cell)) + 1):
                for j in range(int(np.floor(a[1] / cell)), int(np.floor(b[1] / cell)) + 1):
                    self.grid[(i, j)].append(t)

    def heights(self, x, z):
        """all surface heights at (x, z) (top first)"""
        out = []
        for t in self.grid.get((int(np.floor(x / self.cell)), int(np.floor(z / self.cell))), ()):
            p = self.tri[t]
            x0, z0 = p[0, 0], p[0, 2]; x1, z1 = p[1, 0], p[1, 2]; x2, z2 = p[2, 0], p[2, 2]
            d = (z1 - z2) * (x0 - x2) + (x2 - x1) * (z0 - z2)
            if abs(d) < 1e-12:
                continue
            a = ((z1 - z2) * (x - x2) + (x2 - x1) * (z - z2)) / d
            b = ((z2 - z0) * (x - x2) + (x0 - x2) * (z - z2)) / d
            c = 1 - a - b
            if a >= -1e-9 and b >= -1e-9 and c >= -1e-9:
                out.append(a * p[0, 1] + b * p[1, 1] + c * p[2, 1])
        return sorted(out, reverse=True)

    def h(self, x, z):
        hs = self.heights(x, z)
        return hs[0] if hs else np.nan

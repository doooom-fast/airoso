"""rgb.py <img> name:x,y[,r] ...: mean RGB in a (2r+1)^2 box"""
import sys
import numpy as np
from PIL import Image
A = np.asarray(Image.open(sys.argv[1]).convert("RGB")).astype(float)
for arg in sys.argv[2:]:
    name, xy = arg.split(":")
    v = [int(t) for t in xy.split(",")]
    x, y = v[0], v[1]; r = v[2] if len(v) > 2 else 1
    m = A[y - r:y + r + 1, x - r:x + r + 1].reshape(-1, 3).mean(0)
    print(f"{name:12s} ({x},{y}) R {m[0]:5.1f} G {m[1]:5.1f} B {m[2]:5.1f}  g/r {m[1] / max(m[0], 1):.2f} b/r {m[2] / max(m[0], 1):.2f}")
print("-- darkest pixel in each box --")
for arg in sys.argv[2:]:
    name, xy = arg.split(":")
    v = [int(t) for t in xy.split(",")]
    x, y = v[0], v[1]; r = max(v[2] if len(v) > 2 else 1, 4)
    B = A[y - r:y + r + 1, x - r:x + r + 1]
    L = B.mean(2); j, i = np.unravel_index(np.argmin(L), L.shape)
    m = B[j, i]
    print(f"{name:12s} at ({x - r + i},{y - r + j}) R {m[0]:5.1f} G {m[1]:5.1f} B {m[2]:5.1f}  g/r {m[1] / max(m[0], 1):.2f} b/r {m[2] / max(m[0], 1):.2f}")

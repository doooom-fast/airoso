"""Every kerb corner kerb_ab_blend.py baked: the same place in the paint's repeat (frac u) and the same texel, from its
level's copy darkened by that level, as the wrap read before the bake.    python paint_per_corner.py <work dir>..."""
import json, math, sys
from pathlib import Path
import numpy as np
from PIL import Image
for wd in map(Path, sys.argv[1:]):
    d = json.load(open(wd / "fake.json")); kd = d["decl"]["kerbs"]; L = kd["levels"]; R = kd.get("repeats", 1)
    src, rec = next(iter(kd["paint"].items()))
    at = np.asarray(Image.open(wd / "proj" / "textures" / "road_wear" / rec["atlas"]).convert("RGB"))
    paint = np.asarray(Image.open(wd / "proj" / "textures" / src).convert("RGB"))
    W = paint.shape[1]; worst = 0.0; bad = 0; n = 0
    for name in d["uv_before"]:
        b = np.array(d["uv_before"][name]).reshape(-1, 2); a = np.array(d["uv_after"][name]).reshape(-1, 2)
        for (ub, _vb), (ua, _va) in zip(b, a):
            lev = math.floor(ua * L); loc = (ua * L - lev) * R
            worst = max(worst, abs(((loc - ub) + 0.5) % 1.0 - 0.5)); n += 1
            xb = int(math.floor(((ub % 1.0) + 1e-4) % 1.0 * W)); xa = int(math.floor(lev * R * W + (loc + 1e-4) * W))
            want = np.clip(np.round(paint[:, xb].astype(float) * (1 - lev * kd["step"])), 0, 255).astype(np.uint8)
            bad += int(not np.array_equal(at[:, xa], want) or xa // (R * W) != lev)
    print(f"{wd.name}: {n} corners, repeats {R}, worst paint offset {worst:.2e} repeats (float32), texel mismatches {bad}")

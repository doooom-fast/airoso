"""kerb_atlas_hp.png: High Plains' two kerb paint schemes side by side (ledger 0081; kerb.atlas in track.config.json).

u 0-0.5: kerb_bluewhite.png as it was (the blue / white kerbs, round 4). u 0.5-1: the blue / yellow edge stripes, the same
two-band layout (v top half the light band, bottom half the blue), the blue the same paint as the kerbs' and the yellow
the median NAIP 2023 (0.3 m) colour of the stripes' yellow pixels, (205, 194, 137), measured by the kerb_spans colour
classes inside the stripes' measured bands (NAIP's white there reads (222, 232, 238) against this file's (236, 236, 232),
so its colours are near true at this site).

    python tracks/high-plains-lm/textures/make_kerb_atlas.py
"""
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
YELLOW = (205, 194, 137)

bw = Image.open(HERE / "kerb_bluewhite.png").convert("RGB")
w, h = bw.size
blue = bw.getpixel((w // 2, 3 * h // 4))
by = Image.new("RGB", (w, h))
for y in range(h):
    for x in range(w):
        by.putpixel((x, y), YELLOW if y < h // 2 else blue)
atlas = Image.new("RGB", (2 * w, h))
atlas.paste(bw, (0, 0))
atlas.paste(by, (w, 0))
atlas.save(HERE / "kerb_atlas_hp.png")
print(f"kerb_atlas_hp.png {2 * w}x{h}: blue {blue}, yellow {YELLOW}")

"""Add tree-shadowed pavement to mask.raw along the east side (system python, PIL only).

The east side runs under the tree line, and its shadowed half reads dark and blue: B-R 31-38 against
5-14 for shadowed grass (sampled 2026-10-28). Without it the trace hugs the sunlit west edge.
Run after net_extract.py, before tracer.py; delete dist.npy so the tracer recomputes it.
"""
from PIL import Image

W, H = 2130, 3112
ZONE = (1600, 1000, 1950, 2400)  # x0, y0, x1, y1 in mrc_wide px: the east side under the tree line
im = Image.open('mrc_wide.png').convert('RGB')
m = bytearray(open('mask.raw', 'rb').read())
x0, y0, x1, y1 = ZONE
add = set()
for y in range(y0, y1):
    for x in range(x0, x1):
        r, g, b = im.getpixel((x, y))
        lum = (r + g + b) / 3
        if 40 < lum < 120 and 22 <= b - r <= 50 and b >= g:
            add.add((x, y))
# close by 2 px so the shadow class joins the sunlit mask across kerb paint and dapples
grown = {(x + dx, y + dy) for x, y in add for dx in range(-2, 3) for dy in range(-2, 3) if dx * dx + dy * dy <= 4}
for x, y in grown:
    if x0 <= x < x1 and y0 <= y < y1:
        n = sum(1 for dx in range(-2, 3) for dy in range(-2, 3)
                if dx * dx + dy * dy <= 4 and ((x + dx, y + dy) in grown or m[(y + dy) * W + x + dx]))
        if n >= 13:
            m[y * W + x] = 1
open('mask.raw', 'wb').write(bytes(m))
print('shadow pixels', len(add))

"""grid.py <src> <out> x0 y0 x1 y1 scale [step]: a zoomed crop with a labelled source-pixel grid"""
import sys
from PIL import Image, ImageDraw
a = sys.argv
img = Image.open(a[1]).convert("RGB")
x0, y0, x1, y1 = map(int, a[3:7]); sc = float(a[7]); st = int(a[8]) if len(a) > 8 else 20
c = img.crop((x0, y0, x1, y1)).resize((int((x1 - x0) * sc), int((y1 - y0) * sc)), Image.LANCZOS)
d = ImageDraw.Draw(c)
for x in range((x0 // st + 1) * st, x1, st):
    X = (x - x0) * sc
    d.line([(X, 0), (X, c.height)], fill=(255, 255, 0) if x % 100 == 0 else (120, 120, 0), width=1)
    d.text((X + 2, 2), str(x), fill=(255, 255, 0))
for y in range((y0 // st + 1) * st, y1, st):
    Y = (y - y0) * sc
    d.line([(0, Y), (c.width, Y)], fill=(255, 255, 0) if y % 100 == 0 else (120, 120, 0), width=1)
    d.text((2, Y + 2), str(y), fill=(255, 255, 0))
c.save(a[2], quality=90)
print(c.size)

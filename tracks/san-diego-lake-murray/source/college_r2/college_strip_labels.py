"""Adds the scale and labels to college_strip_raw.png -> college_strip.png (Pillow)."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
HERE = Path(__file__).resolve().parent
src = Image.open(HERE / "college_strip_raw.png"); W, Hh = src.size
im = Image.new("RGB", (W + 70, Hh + 96), (250, 250, 248)); im.paste(src, (60, 40)); d = ImageDraw.Draw(im)
try: f = ImageFont.truetype("arial.ttf", 14); fb = ImageFont.truetype("arialbd.ttf", 16)
except OSError: f = fb = ImageFont.load_default()
d.text((60, 10), "College Ave straightened, heading north to the right; west on top. Above: 2022 aerial (yellow = edges of the road as built). Below: surveyed height against the centre line, blue -2 m .. white 0 .. red +6 m (black = built edges).", font=fb, fill=(20, 20, 20))
for v in range(800, 1561, 40):
    x = 60 + (v - 800) * 2
    d.line([x, 40 + Hh, x, 40 + Hh + 6], fill=(60, 60, 60)); d.text((x - 16, 40 + Hh + 8), f"v{v}", font=f, fill=(60, 60, 60))
for base in (40, 40 + 484 + 16):
    for o in (30, 15, 0, -15, -30):
        y = base + (30 - o) * 8
        d.text((8, y - 8), f"{'W' if o > 0 else ('E' if o < 0 else '')}{abs(o):>3} m", font=f, fill=(60, 60, 60))
im.save(HERE / "college_strip.png"); print("saved", im.size)

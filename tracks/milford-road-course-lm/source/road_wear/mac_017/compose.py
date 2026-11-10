"""One comparison per spot: 0.1.5 left, 0.1.7 right, car height over from-above, lightly labelled."""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
W = Path(sys.argv[1]); out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
spots = json.loads((W / "spots.json").read_text())
info = {s["tag"].rsplit("_", 1)[0]: s for s in spots if s["tag"].endswith("_low")}
try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 26)
except Exception:
    font = ImageFont.load_default()
for spot, s in info.items():
    tiles = [[Image.open(W / "stills" / f"{v}_{spot}_{k}.jpg") for v in ("v015", "v017")] for k in ("low", "top")]
    w, h = tiles[0][0].size
    sc = 0.6
    tw, th = int(w * sc), int(h * sc)
    canvas = Image.new("RGB", (2 * tw + 12, 2 * th + 12 + 44), (20, 20, 20))
    d = ImageDraw.Draw(canvas)
    d.text((10, 8), f"{spot.replace('_', ' ')}  (line station {s['station']}, model {s['v_kmh']} km/h, R {s['radius_m']} m)   "
                    f"left 0.1.5  |  right 0.1.7 (aerial tone + rubber, same 4 m detail)",
           fill=(235, 235, 235), font=font)
    for r, row in enumerate(tiles):
        for c, im in enumerate(row):
            canvas.paste(im.resize((tw, th)), (c * (tw + 12), 44 + r * (th + 12)))
    p = out / f"road_wear_015_vs_017_{spot}.jpg"
    canvas.save(p, quality=86)
    print(p, p.stat().st_size)

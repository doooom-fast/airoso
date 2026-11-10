"""draw_inventory.py <naip.jpg> <inventory.json> <out.jpg>: every item drawn on the NAIP frame, labelled (ledger 0082)"""
import json, sys
from PIL import Image, ImageDraw
img = Image.open(sys.argv[1]).convert("RGB")
W, H = img.size
LON0, LAT0, LON1, LAT1 = -83.67, 42.56050328638498, -83.657, 42.57949671361502
px = lambda p: ((p[0] - LON0) / (LON1 - LON0) * W, (LAT1 - p[1]) / (LAT1 - LAT0) * H)
inv = json.load(open(sys.argv[2]))
d = ImageDraw.Draw(img)
COL = {"guardrail_wbeam": (255, 40, 40), "tyre_wall": (40, 200, 255), "container_or_shed": (255, 160, 0), "pad_tent": (255, 160, 0)}
for it in inv["items"]:
    c = COL.get(it["kind"], (255, 0, 255))
    built = it.get("build", True) is True
    if "polyline_lonlat" in it:
        pts = [px(p) for p in it["polyline_lonlat"]]
        d.line(pts, fill=c, width=3 if built else 1)
    else:
        pts = [px(p) for p in it["footprint_lonlat"]]
        d.polygon(pts, outline=c)
    x, y = pts[0]
    d.text((x + 4, y - 4), it["id"] + ("" if built else " (not built)"), fill=(255, 255, 0))
x0, y0, x1, y1 = 380, 820, 1880, 2520
img.crop((x0, y0, x1, y1)).save(sys.argv[3], quality=85)
print("ok")

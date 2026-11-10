import json, sys, math
from PIL import Image, ImageDraw
IMG = "/Volumes/Drive/codex/kerb_work/img/pikes-peak_2023_030.png"
im = Image.open(IMG).convert("RGB")
base = Image.eval(im, lambda v: int(v * 0.6))
d = ImageDraw.Draw(base)
out = {}
for name in ("road_course", "infield_only"):
    doc = json.load(open(f"routes/{name}.json"))
    body = doc.get("data", doc)
    col = body.get("color", "#ff3b30")
    strokes = [s["pts"] for s in body.get("strokes", []) if len(s.get("pts", [])) >= 4]
    L = 0.0
    for pts in strokes:
        xy = [(pts[i], pts[i + 1]) for i in range(0, len(pts), 2)]
        d.line(xy, fill=col, width=4)
        d.ellipse([xy[0][0]-5, xy[0][1]-5, xy[0][0]+5, xy[0][1]+5], fill=col)
        L += sum(math.dist(xy[i], xy[i+1]) for i in range(len(xy)-1)) * 0.3
    out[name] = {"strokes": len(strokes), "drawn_length_m": round(L, 1), "name": body.get("name")}
base.save("sketch_overlay.jpg", quality=88)
print(json.dumps(out, indent=1))

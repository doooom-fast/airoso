"""college_sections.png: measured ground (grey) against the built road (red) at twelve stations, looking north
(west on the left). Vertical x 2. Needs Pillow."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
HERE = Path(__file__).resolve().parent
d = json.loads((HERE / "college_sheet_data.json").read_text(encoding="utf-8"))
off = d["offsets_m"]; S = d["stations"]
CW, CH, cols = 620, 300, 3
rows = (len(S) + cols - 1) // cols
im = Image.new("RGB", (CW * cols, CH * rows + 46), (250, 250, 248)); dr = ImageDraw.Draw(im)
try:
    f = ImageFont.truetype("arial.ttf", 15); fb = ImageFont.truetype("arialbd.ttf", 17)
except OSError:
    f = fb = ImageFont.load_default()
dr.text((12, 10), "College Ave, looking north: measured ground (USGS 2024 lidar, grey) and the road as built in 0.20.2 (red). West is left. Heights x 2.", font=fb, fill=(20, 20, 20))
PXM = 9.0; VS = 2.0
for k, s in enumerate(S):
    x0 = (k % cols) * CW; y0 = 46 + (k // cols) * CH
    cx = x0 + CW // 2; base = y0 + CH - 70
    dr.rectangle([x0 + 4, y0 + 4, x0 + CW - 4, y0 + CH - 4], outline=(200, 200, 200))
    def P(o, y):                      # + offset = west = left on the page
        return (cx - o * PXM, base - (y - s["y_line"]) * PXM * VS)
    for g in range(-2, 9, 2):         # height grid, m above the line
        yy = base - g * PXM * VS
        dr.line([x0 + 30, yy, x0 + CW - 10, yy], fill=(228, 228, 228))
        dr.text((x0 + 8, yy - 8), f"{g:+d}", font=f, fill=(140, 140, 140))
    pts = [P(o, y) for o, y in zip(off, s["measured"]) if y is not None]
    run = []
    for o, y in zip(off, s["measured"]):
        if y is None:
            if len(run) > 1: dr.line(run, fill=(90, 90, 90), width=3)
            run = []
        else:
            run.append(P(o, y))
    if len(run) > 1: dr.line(run, fill=(90, 90, 90), width=3)
    run = []
    for o, y in zip(off, s["built"]):
        if y is None:
            if len(run) > 1: dr.line(run, fill=(210, 40, 40), width=3)
            run = []
        else:
            run.append(P(o, y))
    if len(run) > 1: dr.line(run, fill=(210, 40, 40), width=3)
    dr.text((x0 + 14, y0 + 10), f"v{s['v']}  ({s['s_m']:.0f} m along the lap)", font=fb, fill=(20, 20, 20))
    for o in (-30, -20, -10, 0, 10, 20, 30):
        px = cx - o * PXM
        dr.line([px, y0 + CH - 34, px, y0 + CH - 28], fill=(120, 120, 120))
        dr.text((px - 12, y0 + CH - 26), f"{abs(o)}", font=f, fill=(120, 120, 120))
    dr.text((x0 + 14, y0 + CH - 48), "west", font=f, fill=(120, 120, 120)); dr.text((x0 + CW - 50, y0 + CH - 48), "east", font=f, fill=(120, 120, 120))
im.save(HERE / "college_sections.png")
print("saved", im.size)

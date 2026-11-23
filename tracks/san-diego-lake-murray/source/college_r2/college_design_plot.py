"""college_design.png: the design in plan (edges against the built slab) and in long profile (each carriageway's
centre height against the built road). Needs Pillow; reads college_design.json."""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
D = json.loads((HERE / "college_design.json").read_text(encoding="utf-8"))
R = D["stations"]
W, H1, H2 = 1500, 330, 420
im = Image.new("RGB", (W + 110, H1 + H2 + 200), (250, 250, 248))
d = ImageDraw.Draw(im)
try:
    f = ImageFont.truetype("arial.ttf", 14)
    fb = ImageFont.truetype("arialbd.ttf", 16)
except OSError:
    f = fb = ImageFont.load_default()
s0, s1 = R[0]["s_m"], R[-1]["s_m"]
X0 = 80


def px(s):
    return X0 + (s - s0) / (s1 - s0) * W


COL = {"sb_outer": (60, 120, 255), "sb_inner": (0, 190, 230), "nb_inner": (255, 150, 0), "nb_outer": (230, 50, 50)}
# --- plan -----------------------------------------------------------------------------------------------------------------
top = 50
d.text((X0, 12), "College Ave realism+, the design. Plan: west on top, north to the right. Blue = southbound, orange / red = northbound, green = the planted bank.", font=fb, fill=(20, 20, 20))


def py(o):
    return top + H1 / 2 - o * (H1 / 44.0)


for o in (-20, -10, 0, 10, 20):
    d.line([X0, py(o), X0 + W, py(o)], fill=(225, 225, 225))
    d.text((10, py(o) - 8), f"{'W' if o > 0 else ('E' if o < 0 else '')} {abs(o)} m", font=f, fill=(110, 110, 110))
poly = [(px(r["s_m"]), py(r["sb_inner"]["offset_m"])) for r in R] + [(px(r["s_m"]), py(r["nb_inner"]["offset_m"])) for r in reversed(R)]
d.polygon(poly, fill=(150, 195, 140))
for key, col in COL.items():
    d.line([(px(r["s_m"]), py(r[key]["offset_m"])) for r in R], fill=col, width=3)
    for r in R:
        if r[key]["bridged"]:
            d.point((px(r["s_m"]), py(r[key]["offset_m"]) + 5), fill=(0, 0, 0))
# --- profile --------------------------------------------------------------------------------------------------------------
top2 = top + H1 + 60
d.text((X0, top2 - 28), "Long profile: height of each carriageway's centre. Black dashes = the road as built. Black dots under an edge in the plan = bridged, not measured.", font=fb, fill=(20, 20, 20))
ys = [0.5 * (r["nb_inner"]["y"] + r["nb_outer"]["y"]) for r in R] + [0.5 * (r["sb_inner"]["y"] + r["sb_outer"]["y"]) for r in R]
y0, y1 = min(ys) - 1, max(ys) + 1


def pv(y):
    return top2 + H2 - (y - y0) / (y1 - y0) * H2


g = int(y0 // 5) * 5
while g <= y1:
    if g >= y0:
        d.line([X0, pv(g), X0 + W, pv(g)], fill=(225, 225, 225))
        d.text((10, pv(g) - 8), f"{g + 100.8:.0f} m", font=f, fill=(110, 110, 110))
    g += 5
bc = [(px(r["s_m"]), pv(0.5 * (r["sb_inner"]["y_built"] + r["nb_inner"]["y_built"]))) for r in R]
for k in range(0, len(bc) - 1, 2):
    d.line([bc[k], bc[k + 1]], fill=(0, 0, 0), width=2)
d.line([(px(r["s_m"]), pv(0.5 * (r["sb_inner"]["y"] + r["sb_outer"]["y"]))) for r in R], fill=(40, 110, 240), width=3)
d.line([(px(r["s_m"]), pv(0.5 * (r["nb_inner"]["y"] + r["nb_outer"]["y"]))) for r in R], fill=(230, 60, 40), width=3)
for r in R:
    if r["v"] % 40 == 0:
        x = px(r["s_m"])
        d.line([x, top2 + H2, x, top2 + H2 + 6], fill=(60, 60, 60))
        d.text((x - 16, top2 + H2 + 8), f"v{r['v']}", font=f, fill=(60, 60, 60))
c = D["checks"]
d.text((X0, top2 + H2 + 34), f"Northbound over southbound up to {c['northbound_over_southbound_m']['max']} m (v{c['northbound_over_southbound_m']['at_v']}). "
       f"Steepest grade: northbound {c['long_grade_pct']['northbound_max']} %, southbound {c['long_grade_pct']['southbound_max']} %, as built {c['long_grade_pct']['built_centre_max']} %. "
       f"Bank up to {c['bank_slope_pct']['max']} %.", font=f, fill=(20, 20, 20))
im.save(HERE / "college_design.png")
print("saved", im.size)

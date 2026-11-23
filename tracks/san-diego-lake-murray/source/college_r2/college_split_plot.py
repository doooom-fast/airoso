"""college_split.png: the split's DATA (college_split.data.json) in plan and in long profile. Needs Pillow.
Plan: offsets from the built road's line, west on top, north to the right. Profile: the two lines' heights."""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
S = json.loads((HERE / "college_split.data.json").read_text(encoding="utf-8"))
M, Z, E, R = S["mainline"], S["lap_zone"], S["edges"], S["report"]
A0, A1 = M["from_v"], M["to_v"]
NOSE, TAIL = E["v"][0], E["v"][-1]
W, H1, H2 = 1500, 360, 400
X0 = 80
im = Image.new("RGB", (W + 110, H1 + H2 + 230), (250, 250, 248))
d = ImageDraw.Draw(im)
try:
    f = ImageFont.truetype("arial.ttf", 14)
    fb = ImageFont.truetype("arialbd.ttf", 16)
except OSError:
    f = fb = ImageFont.load_default()
SB, NB, BANK, GREY = (60, 120, 255), (230, 60, 50), (150, 195, 140), (120, 120, 120)
SB_LINE, NB_LINE = (10, 50, 190), (170, 20, 20)


def px(v):
    return X0 + (v - A0) / (A1 - A0) * W


top = 50
d.text((X0, 12), "College Ave split, the data. Plan: blue = the mainline (southbound road), red = the new piece (northbound road), "
       "green = the bank between.", font=fb, fill=(20, 20, 20))


def py(o):
    return top + H1 / 2 - o * (H1 / 40.0)


for o in (-15, -10, -5, 0, 5, 10, 15):
    d.line([X0, py(o), X0 + W, py(o)], fill=(228, 228, 228))
    d.text((8, py(o) - 8), f"{'W' if o > 0 else ('E' if o < 0 else '')} {abs(o)} m", font=f, fill=(110, 110, 110))
vs = E["v"]


def band(upper, lower, fill):
    d.polygon([(px(v), py(o)) for v, o in zip(vs, upper)] + [(px(v), py(o)) for v, o in zip(reversed(vs), reversed(lower))], fill=fill)


band(E["sb_west_m"], E["sb_east_m"], (205, 222, 255))
band(E["nb_west_m"], E["nb_east_m"], (255, 214, 208))
band(E["sb_east_m"], E["nb_west_m"], BANK)
# the two forks: the whole built road, paved by one deck each. The built west edge = the mainline's line + half its
# width (it never moves); the built road is symmetric about its old line, so the east edge is its mirror.
zone = list(range(A0, A1 + 1))
for a, b in ((A0, NOSE), (TAIL, A1)):
    ks = [v - A0 for v in range(a, b + 1)]
    wst = [M["offset_m"][k] + 0.5 * M["widths_m"][k] for k in ks]
    d.polygon([(px(A0 + k), py(o)) for k, o in zip(ks, wst)] + [(px(A0 + k), py(-o)) for k, o in zip(reversed(ks), reversed(wst))],
              fill=(232, 232, 226))
    d.line([(px(A0 + k), py(o)) for k, o in zip(ks, wst)], fill=GREY, width=2)
    d.line([(px(A0 + k), py(-o)) for k, o in zip(ks, wst)], fill=GREY, width=2)
for key, col in (("sb_west_m", SB), ("sb_east_m", SB), ("nb_west_m", NB), ("nb_east_m", NB)):
    d.line([(px(v), py(o)) for v, o in zip(vs, E[key])], fill=col, width=2)
d.line([X0, py(0), X0 + W, py(0)], fill=(0, 0, 0))
d.line([(px(v), py(o)) for v, o in zip(zone, M["offset_m"])], fill=SB_LINE, width=3)
d.line([(px(v), py(o)) for v, o in zip(zone, Z["offset_m"])], fill=NB_LINE, width=3)
for v, lab in ((A0, f"v{A0}"), (NOSE, f"v{NOSE}: the island begins"), (TAIL, f"v{TAIL}: it ends"), (A1, f"v{A1}")):
    d.line([px(v), top, px(v), top + H1], fill=(90, 90, 90))
    tw = d.textlength(lab, font=f)
    d.text((min(px(v) + 4, X0 + W - tw), top + H1 - 18), lab, font=f, fill=(60, 60, 60))
d.text((px(A0) + 8, top + 6), "south fork: one deck", font=f, fill=(60, 60, 60))
d.text((px(TAIL) + 8, top + 6), "north fork: one deck", font=f, fill=(60, 60, 60))
d.text((px(1290), py(13.2) - 8), "mainline = southbound road", font=f, fill=SB_LINE)
d.text((px(1290), py(-13.9) - 8), "college_nb = northbound road (Speedway)", font=f, fill=NB_LINE)
d.text((X0, top + H1 + 4), "Thick lines = the two reference lines (blue the mainline, red the Speedway lap). The black line is the built "
       "road's line, where the mainline was.", font=f, fill=(60, 60, 60))
# --- profile ----------------------------------------------------------------------------------------------------------------
top2 = top + H1 + 70
d.text((X0, top2 - 28), "Long profile: line heights. Black dashes = the built line. The red lap climbs up to "
       f"{R['piece']['over_mainline_m']['max']} m over the blue mainline.", font=fb, fill=(20, 20, 20))
ym = [p[1] for p in M["points_xyz_m"]]
yl = [p[1] for p in Z["points_xyz_m"]]
yb = S["built_line_y"]
y0, y1 = min(ym + yl + yb) - 1, max(ym + yl + yb) + 1


def pv(y):
    return top2 + H2 - (y - y0) / (y1 - y0) * H2


g = int(y0 // 5) * 5
while g <= y1:
    if g >= y0:
        d.line([X0, pv(g), X0 + W, pv(g)], fill=(228, 228, 228))
        d.text((8, pv(g) - 8), f"{g} m", font=f, fill=(110, 110, 110))
    g += 5
d.line([(px(v), pv(y)) for v, y in zip(zone, ym)], fill=SB_LINE, width=3)
d.line([(px(v), pv(y)) for v, y in zip(zone, yl)], fill=NB_LINE, width=3)
for k in range(0, len(yb) - 1, 2):
    d.line([px(A0 + k), pv(yb[k]), px(A0 + k + 1), pv(yb[k + 1])], fill=(0, 0, 0), width=1)
for v in (A0, NOSE, TAIL, A1):
    d.line([px(v), top2, px(v), top2 + H2], fill=(150, 150, 150))
g = R["heights"]["grade_pct_min_max_and_largest_step_between_segments"]
t = R["mainline"]["largest_turn_between_segments_deg"]
d.text((X0, top2 + H2 + 10), f"Steepest grade: built line {g['built_line'][0]} / +{g['built_line'][1]} %, mainline {g['mainline'][0]} / "
       f"+{g['mainline'][1]} %, lap {g['lap'][0]} / +{g['lap'][1]} %.   Largest turn between 3 m segments: built {t['old']} deg, "
       f"mainline {t['new']} deg, lap {R['lap']['largest_turn_between_segments_deg']} deg.", font=f, fill=(60, 60, 60))
b = R["bank_between_the_roads_m"]
d.text((X0, top2 + H2 + 32), f"Bank between the roads: {b['at_nose']} m where the island begins, up to {b['max']} m, {b['at_tail']} m where it "
       f"ends (never negative).   Road widths: southbound {R['mainline']['width_m']['two_roads_min']} to "
       f"{R['mainline']['width_m']['two_roads_max']} m, northbound {R['piece']['width_m']['min']} to {R['piece']['width_m']['max']} m.",
       font=f, fill=(60, 60, 60))
im.save(HERE / "college_split.png")
print("wrote college_split.png", im.size)

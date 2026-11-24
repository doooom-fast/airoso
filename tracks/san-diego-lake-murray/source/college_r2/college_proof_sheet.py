"""college_proof.jpg: the proof scene's stills, before (left) and after (right), three views. Needs Pillow.

    python college_proof_sheet.py <the proof scene's out dir>"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
src = Path(sys.argv[1])
VIEWS = (("1_northbound_v1215", "Driving north on the northbound side, about 3,640 m along the lap"),
         ("2_southbound_v1410", "Driving south on the southbound side, about 4,220 m along the lap"),
         ("3_from_the_southwest", "From the south-west, 85 m up"))
W, H = 800, 360
sheet = Image.new("RGB", (2 * W + 30, len(VIEWS) * (H + 44) + 52), (250, 250, 248))
d = ImageDraw.Draw(sheet)
try:
    f = ImageFont.truetype("arial.ttf", 15)
    fb = ImageFont.truetype("arialbd.ttf", 18)
except OSError:
    f = fb = ImageFont.load_default()
d.text((10, 12), "College Ave: as built in 0.20.2 (left) and the design on the surveyed ground (right). A shape study: no paint, lamps, trees or closed seams.", font=fb, fill=(20, 20, 20))
for k, (name, label) in enumerate(VIEWS):
    y = 52 + k * (H + 44)
    d.text((10, y), label, font=f, fill=(40, 40, 40))
    for c, state in enumerate(("before", "after")):
        im = Image.open(src / f"proof_{name}_{state}.png").convert("RGB").resize((W, H), Image.LANCZOS)
        sheet.paste(im, (10 + c * (W + 10), y + 22))
sheet.save(HERE / "college_proof.jpg", quality=86)
print("saved", sheet.size)

"""Generate the regulatory, warning and street-name sign faces Denver Grand Prix's junctions need (ledger 0096,
PLAN §4b / DOSSIER §8) — deterministic, self-made (CC0). tools/make_sign_textures.py drew the W1 arrows; this
extends the procedural MUTCD set. MUTCD sign designs are in the public domain (MUTCD Introduction; 17 U.S.C. 105);
nothing is copied from a sign pack or a photograph, and the letters are this repo's own stroke alphabet
(tools/street_furniture_draw.py), an APPROXIMATION of the FHWA Standard Alphabets.

ALREADY OWNED, NOT USED: the Dropbox "US traffic signs pack" (ASSET-LIBRARY: `obj/traffic signs-01.obj` + 57 sign
JPGs) covers much of this set, but its licence is UNRECORDED, so it cannot go in the CC0 package. These faces are
its owned replacement.

HOW ACCURATE. Sizes are the MUTCD's (2009 edition, Table 2B-1 and the sections named per face). The LAYOUTS (where
the legend sits, arrow proportions, the pedestrian figure) were drawn from knowledge of the standard signs, not
measured off the Standard Highway Signs drawings, and the MUTCD was not re-read in the session that wrote this:
each is a recognisable face of the right size and colours, not a sheet-exact copy. Denver's street-name blade style
(green, white capitals, small direction prefix and street-type suffix) is from memory and UNVERIFIED: check it
against a street-level frame before a blade is placed. The bus-lane legend is a guess at what Denver posts.

THE PLATE UV LAYOUT (the contract with the engine, PLAN §4b engine work 8):
  * every face texture covers its sign's BOUNDING RECTANGLE exactly, edge to edge: u = 0 at the left edge, u = 1 at
    the right, v = 0 at the bottom, v = 1 at the top, as seen by the reader facing the sign;
  * the texture is resampled to a power of two each way (L7), so texels are not square: a 24 x 30 in face is
    512 x 512 px. The plate, not the texture, carries the aspect;
  * outside the sign's outline (an octagon's corners, a diamond's, a circle's, rounded corners) alpha is 0, and the
    COLOUR there is the face's own edge colour, not black: a plate cut to the outline needs no alpha test, and an
    uncut alpha-tested rectangle shows no dark fringe;
  * assets/models/sign_plate_<shape>.obj are plates cut to the outline with exactly these UVs: object FACE
    (material SIGNFACE, to be bound per face) looking along +z, object BACK (SIGNBACK, bare aluminium) behind it;
    origin = the plate's centre; metres;
  * the prep must leave these meshes' UVs alone (today it overwrites every non-exempt mesh with a planar
    projection, which collapses a vertical plate to a line).
Mounting, for the placer: MUTCD 2A.18 (bottom of the sign at least 7 ft above the walk where people park or walk),
2A.19 (at least 2 ft from the kerb face, 1 ft where the walk is narrow).

OUTPUT: assets/textures/mutcd_<code>.png, assets/models/sign_plate_<shape>.obj + sign_faces.json, and the
street-name blades in tracks/denver-grand-prix/textures/blades/blade_<street>.png (a track's own tiles live with
the track).

    python tools/make_sign_faces.py            # writes everything
    python tools/make_sign_faces.py --check    # exit 1 if a committed file is missing or differs
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from street_furniture_mesh import IN, Model, write_or_check          # noqa: E402

AIROSO = Path(__file__).resolve().parents[1]
OUT = AIROSO / "assets" / "models"
TEX = AIROSO / "assets" / "textures"
BLADES = AIROSO / "tracks" / "denver-grand-prix" / "textures" / "blades"
MAKER = "tools/make_sign_faces.py"

WHITE, BLACK = (245, 245, 245), (20, 20, 20)
RED, GREEN = (183, 28, 36), (0, 105, 72)          # approximations of the FHWA red and green, as YELLOW is
YELLOW, FYG = (255, 205, 0), (200, 235, 20)       # YELLOW = make_sign_textures.py's; FYG = fluorescent yellow-green

# the lap's streets and the streets that meet it, read from tracks/denver-grand-prix/source/osm.json (OSM as of
# 2026-11-23): the `name` of every lap way (data/lap_ways.plan.json) and of every driveable way sharing a node with one
DENVER_STREETS = [
    "12th Street", "14th Street", "15th Street", "Arapahoe Street", "Auraria Parkway", "Bannock Street", "Blake Street",
    "Champa Street", "Cherokee Street", "Cheyenne Place", "Court Place", "Curtis Street", "Delaware Street",
    "East 14th Avenue", "East Colfax Avenue", "Elati Street", "Fox Street", "Galapago Street", "Glenarm Place",
    "Grant Street", "Larimer Street", "Lawrence Street", "Logan Street", "Market Street", "North Broadway",
    "North Kalamath Street", "North Lincoln Street", "North Santa Fe Drive", "North Speer Boulevard",
    "Pennsylvania Street", "Saint Francis Way", "Sherman Street", "Stout Street", "Tremont Place", "Welton Street",
    "West 14th Avenue", "West 14th Avenue Parkway", "West Colfax Avenue",
]
PREFIX = {"North": "N", "South": "S", "East": "E", "West": "W"}
SUFFIX = {"Street": "ST", "Avenue": "AVE", "Boulevard": "BLVD", "Parkway": "PKWY", "Place": "PL", "Drive": "DR", "Way": "WAY", "Court": "CT"}
BLADE_IN = (36.0, 9.0)                            # [typical] post-mounted blade; MUTCD 2D.43 fixes the letter height, not the blade


def blade_legend(street: str):
    """'North Speer Boulevard' -> ('N', 'SPEER', 'BLVD')"""
    t = street.split()
    pre = PREFIX.get(t[0], "") if len(t) > 1 else ""
    if pre:
        t = t[1:]
    suf = SUFFIX.get(t[-1], "") if len(t) > 1 else ""
    if suf:
        t = t[:-1]
    name = " ".join(SUFFIX.get(w, w) if i else w for i, w in enumerate(t)).upper().replace("SAINT", "ST")
    return pre, name, suf


def blade_file(street: str) -> str:
    return "blade_" + street.lower().replace(" ", "_") + ".png"


# ---- the canvas: drawing in inches, y down -------------------------------------------------------------------------
class Canvas:
    def __init__(self, w_in: float, h_in: float, shape: str, bleed, long_px: int = 512):
        from PIL import Image, ImageDraw
        from street_furniture_draw import SS, pot
        self.w, self.h, self.shape = w_in, h_in, shape
        self.size = (long_px, pot(long_px * h_in / w_in, long_px)) if w_in >= h_in else (pot(long_px * w_in / h_in, long_px), long_px)
        self.ppi = SS * max(self.size[0] / w_in, self.size[1] / h_in)
        n = (int(round(w_in * self.ppi)), int(round(h_in * self.ppi)))
        self.rgb = Image.new("RGB", n, bleed)
        self.d = ImageDraw.Draw(self.rgb)
        self.mask = Image.new("L", n, 0)
        md = ImageDraw.Draw(self.mask)
        if shape == "rect":
            md.rounded_rectangle([0, 0, n[0] - 1, n[1] - 1], radius=min(1.5, 0.12 * min(w_in, h_in)) * self.ppi, fill=255)
        elif shape == "circle":
            md.ellipse([0, 0, n[0] - 1, n[1] - 1], fill=255)
        else:
            md.polygon([self.p(q) for q in outline(shape, w_in, h_in)], fill=255)

    def p(self, q):
        return (q[0] * self.ppi, q[1] * self.ppi)

    def poly(self, pts, fill):
        self.d.polygon([self.p(q) for q in pts], fill=fill)

    def rect(self, x0, y0, x1, y1, fill):
        self.d.rectangle([*self.p((x0, y0)), *self.p((x1, y1))], fill=fill)

    def border(self, inset, width, colour, radius=1.5):
        i = inset * self.ppi
        self.d.rounded_rectangle([i, i, self.w * self.ppi - 1 - i, self.h * self.ppi - 1 - i], radius=max(radius - inset, 0.2) * self.ppi,
                                 outline=colour, width=int(round(width * self.ppi)))

    def ring(self, cx, cy, r, width, colour):
        self.d.ellipse([*self.p((cx - r, cy - r)), *self.p((cx + r, cy + r))], outline=colour, width=int(round(width * self.ppi)))

    def disc(self, cx, cy, r, colour):
        self.d.ellipse([*self.p((cx - r, cy - r)), *self.p((cx + r, cy + r))], fill=colour)

    def line(self, pts, width, colour, round_ends=False):
        from street_furniture_draw import thick_line
        thick_line(self.d, [self.p(q) for q in pts], width * self.ppi, colour, round_ends)

    def text(self, s, cx, top, cap, colour, max_w=None):
        from street_furniture_draw import draw_text
        draw_text(self.d, s, cx * self.ppi, top * self.ppi, cap * self.ppi, colour, max_w=None if max_w is None else max_w * self.ppi)

    def arrow(self, path, shaft, head_len, head_w, colour):
        """a thick path ending in a triangular head whose TIP is ``head_len`` past the path's last point"""
        (ax, ay), (bx, by) = path[-2], path[-1]
        L = math.hypot(bx - ax, by - ay)
        ux, uy = (bx - ax) / L, (by - ay) / L
        self.line(path, shaft, colour)
        self.poly([(bx + ux * head_len, by + uy * head_len), (bx - uy * head_w / 2, by + ux * head_w / 2), (bx + uy * head_w / 2, by - ux * head_w / 2)], colour)

    def person(self, cx, cy, height, colour, facing=1):
        """the walking-person symbol in a box ``height`` tall centred on (cx, cy)"""
        f = lambda x, y: (cx + facing * (x - 0.5) * height, cy + (0.5 - y) * height)
        self.disc(*f(0.52, 0.905), 0.085 * height, colour)
        for pts, t in (([(0.50, 0.78), (0.46, 0.46)], 0.135), ([(0.51, 0.75), (0.68, 0.57), (0.79, 0.53)], 0.06),
                       ([(0.49, 0.75), (0.33, 0.61), (0.29, 0.47)], 0.06), ([(0.47, 0.47), (0.60, 0.26), (0.66, 0.03)], 0.078),
                       ([(0.45, 0.47), (0.36, 0.26), (0.22, 0.04)], 0.078)):
            self.line([f(*q) for q in pts], t * height, colour, round_ends=True)

    def image(self):
        from street_furniture_draw import finish
        return finish(self.rgb, self.mask, self.size)


def outline(shape: str, w: float, h: float):
    """the sign's outline in its bounding rectangle, inches, y down, counter-clockwise on screen"""
    if shape == "rect":
        return [(0, 0), (w, 0), (w, h), (0, h)]
    if shape == "octagon":
        k = w / (2 + math.sqrt(2))
        return [(k, 0), (w - k, 0), (w, k), (w, h - k), (w - k, h), (k, h), (0, h - k), (0, k)]
    if shape == "diamond":
        return [(w / 2, 0), (w, h / 2), (w / 2, h), (0, h / 2)]
    if shape == "circle":
        return [(w / 2 + w / 2 * math.cos(2 * math.pi * k / 16), h / 2 + h / 2 * math.sin(2 * math.pi * k / 16)) for k in range(16)]
    raise ValueError(shape)


def _inset(pts, w, h, i):
    s = (w - 2 * i) / w
    return [(w / 2 + (x - w / 2) * s, h / 2 + (y - h / 2) * s) for x, y in pts]


# ---- the faces ----------------------------------------------------------------------------------------------------
def r1_1():
    c = Canvas(30, 30, "octagon", WHITE)
    c.poly(_inset(outline("octagon", 30, 30), 30, 30, 0.75), RED)
    c.text("STOP", 15, 10, 10, WHITE, max_w=24)
    return c


def r6_1(side):
    c = Canvas(36, 12, "rect", BLACK)
    c.border(0.375, 0.45, WHITE)
    m = (lambda x: x) if side == "r" else (lambda x: 36 - x)
    c.poly([(m(x), y) for x, y in ((2.5, 3.25), (25.5, 3.25), (25.5, 1.5), (33.75, 6), (25.5, 10.5), (25.5, 8.75), (2.5, 8.75))], WHITE)
    c.text("ONE WAY", m(14.0), 4.25, 3.5, BLACK, max_w=21)
    return c


def r6_2(side):
    c = Canvas(24, 30, "rect", WHITE)
    c.border(0.5, 0.625, BLACK)
    m = (lambda x: x) if side == "r" else (lambda x: 24 - x)
    c.text("ONE", 12, 3.75, 5, BLACK)
    c.poly([(m(x), y) for x, y in ((3, 13.0), (14.5, 13.0), (14.5, 10.5), (21, 15), (14.5, 19.5), (14.5, 17.0), (3, 17.0))], BLACK)
    c.text("WAY", 12, 21.25, 5, BLACK)
    return c


def r5_1():
    c = Canvas(30, 30, "rect", WHITE)
    c.disc(15, 15, 14, RED)
    c.rect(4.5, 12.75, 25.5, 17.25, WHITE)
    c.text("DO NOT", 15, 6.75, 3, WHITE)
    c.text("ENTER", 15, 20.25, 3, WHITE)
    return c


def r2_1(mph):
    c = Canvas(24, 30, "rect", WHITE)
    c.border(0.5, 0.625, BLACK)
    c.text("SPEED", 12, 3, 4, BLACK, max_w=19)
    c.text("LIMIT", 12, 8.75, 4, BLACK, max_w=19)
    c.text(str(mph), 12, 15.5, 10, BLACK)
    return c


def _prohibit(c):
    c.ring(12, 12, 10.2, 1.9, RED)
    c.line([(12 - 6.6, 12 - 6.6), (12 + 6.6, 12 + 6.6)], 1.9, RED)


def r3_turn(side):
    """R3-1 (no right turn) / R3-2 (no left turn)"""
    c = Canvas(24, 24, "rect", WHITE)
    c.border(0.5, 0.5, BLACK)
    m = (lambda x: x) if side == "r" else (lambda x: 24 - x)
    c.arrow([(m(9.0), 19.0), (m(9.0), 10.5), (m(13.5), 10.5)], 2.6, 4.6, 6.6, BLACK)
    _prohibit(c)
    return c


def r3_4():
    c = Canvas(24, 24, "rect", WHITE)
    c.border(0.5, 0.5, BLACK)
    arc = [(12 + 3.6 * math.cos(math.radians(a)), 10.5 - 3.6 * math.sin(math.radians(a))) for a in range(0, 181, 15)]
    c.arrow([(15.6, 19.0)] + arc + [(8.4, 13.0)], 2.4, 4.4, 6.2, BLACK)
    _prohibit(c)
    return c


def r3_5(kind):
    """R3-5L / R3-5R mandatory turn, R3-5a through only: the arrow over ONLY"""
    c = Canvas(30, 36, "rect", WHITE)
    c.border(0.5, 0.625, BLACK)
    if kind == "a":
        c.arrow([(15, 22), (15, 11)], 3.2, 6.5, 9.0, BLACK)
    else:
        m = (lambda x: x) if kind == "r" else (lambda x: 30 - x)
        c.arrow([(m(11.0), 22.0), (m(11.0), 10.0), (m(18.0), 10.0)], 3.2, 6.5, 9.0, BLACK)
    c.text("ONLY", 15, 25.5, 6, BLACK, max_w=24)
    return c


def r3_6(side):
    """R3-6 optional movement: one stem, a through head and a turn head"""
    c = Canvas(30, 36, "rect", WHITE)
    c.border(0.5, 0.625, BLACK)
    m = (lambda x: x) if side == "r" else (lambda x: 30 - x)
    c.arrow([(m(12.0), 31.0), (m(12.0), 11.5)], 3.0, 6.5, 8.5, BLACK)
    c.arrow([(m(12.0), 26.0), (m(12.0), 19.5), (m(18.5), 19.5)], 3.0, 5.5, 8.0, BLACK)
    return c


def r3_7(side):
    c = Canvas(30, 30, "rect", WHITE)
    c.border(0.5, 0.625, BLACK)
    word = "LEFT" if side == "l" else "RIGHT"
    c.text(word + " LANE", 15, 4.25, 4, BLACK, max_w=25)
    c.text("MUST", 15, 13, 4, BLACK, max_w=25)
    c.text("TURN " + word, 15, 21.75, 4, BLACK, max_w=25)
    return c


def r3_8(kind):
    """R3-8 advance lane control, two lanes: 'lt' = left-turn-only | through, 'tr' = through | right-turn-only"""
    c = Canvas(30, 30, "rect", WHITE)
    c.border(0.5, 0.625, BLACK)
    c.line([(15, 3.5), (15, 26.5)], 0.5, BLACK)
    m = (lambda x: x) if kind == "tr" else (lambda x: 30 - x)
    c.arrow([(m(8.0), 24.0), (m(8.0), 10.0)], 2.2, 4.6, 6.2, BLACK)                            # the through lane
    c.arrow([(m(19.5), 19.0), (m(19.5), 9.0), (m(22.0), 9.0)], 2.2, 4.2, 6.0, BLACK)             # the turn lane
    c.text("ONLY", m(22.0), 21.5, 2.75, BLACK, max_w=10.5)
    return c


def r3_11_bus():
    c = Canvas(24, 30, "rect", WHITE)
    c.border(0.5, 0.625, BLACK)
    for s, top in (("RIGHT", 3.25), ("LANE", 9.25), ("BUS", 15.75), ("ONLY", 21.75)):
        c.text(s, 12, top, 4.5, BLACK, max_w=19)
    return c


def r10_3():
    c = Canvas(9, 12, "rect", WHITE, long_px=256)
    c.border(0.25, 0.25, BLACK, radius=0.75)
    for s, top in (("PUSH", 0.9), ("BUTTON", 2.4), ("FOR", 3.9)):
        c.text(s, 4.5, top, 1.1, BLACK, max_w=7)
    c.person(4.5, 7.1, 3.4, BLACK, facing=-1)
    c.arrow([(6.6, 10.3), (3.6, 10.3)], 0.55, 1.3, 1.6, BLACK)
    return c


def r15_1(word):
    c = Canvas(48, 9, "rect", WHITE)
    if word == "railroad":                       # the CROSSING blade lies over this one's middle: the word is split
        c.text("RAIL", 11.5, 2, 5, BLACK)
        c.text("ROAD", 36.5, 2, 5, BLACK)
    else:
        c.text("CROSSING", 24, 2, 5, BLACK, max_w=44)
    return c


def w10_1():
    c = Canvas(36, 36, "circle", YELLOW)
    c.ring(18, 18, 17.4, 0.75, BLACK)
    k = 16.4 / math.sqrt(2)
    c.line([(18 - k, 18 - k), (18 + k, 18 + k)], 2.6, BLACK)
    c.line([(18 - k, 18 + k), (18 + k, 18 - k)], 2.6, BLACK)
    c.text("R", 6.6, 14.5, 7, BLACK)
    c.text("R", 29.4, 14.5, 7, BLACK)
    return c


def w11_2(colour):
    s = 30 * math.sqrt(2)                        # the diamond's bounding square
    c = Canvas(s, s, "diamond", colour)
    c.line(_inset(outline("diamond", s, s), s, s, 1.4) + [_inset(outline("diamond", s, s), s, s, 1.4)[0]], 0.8, BLACK)
    c.person(s / 2, s / 2, 17.5, BLACK, facing=-1)
    return c


def blade(street):
    from street_furniture_draw import text_width
    w, h = BLADE_IN
    c = Canvas(w, h, "rect", GREEN)
    c.border(0.3, 0.35, WHITE, radius=1.0)
    pre, name, suf = blade_legend(street)
    big, small, gap, room = 5.5, 2.75, 1.1, w - 3.2
    side = sum(text_width(t, small) + gap for t in (pre, suf) if t)
    nw = min(text_width(name, big), room - side)
    x = (w - (nw + side)) / 2
    if pre:
        c.text(pre, x + text_width(pre, small) / 2, 1.75 + big - small, small, WHITE)
        x += text_width(pre, small) + gap
    c.text(name, x + nw / 2, 1.75, big, WHITE, max_w=nw + 0.01)
    if suf:
        c.text(suf, x + nw + gap + text_width(suf, small) / 2, 1.75, small, WHITE)
    return c


# code -> (title, MUTCD reference, size note, builder). The file is mutcd_<code>.png.
FACES = {
    "r1-1": ("STOP", "MUTCD 2B.05; Table 2B-1: 30 x 30 in (36 on multi-lane approaches)", r1_1),
    "r6-1l": ("ONE WAY, arrow left", "MUTCD 2B.40; Table 2B-1: 36 x 12 in", lambda: r6_1("l")),
    "r6-1r": ("ONE WAY, arrow right", "MUTCD 2B.40; Table 2B-1: 36 x 12 in", lambda: r6_1("r")),
    "r6-2l": ("ONE WAY, upright, arrow left", "MUTCD 2B.40; Table 2B-1: 24 x 30 in", lambda: r6_2("l")),
    "r6-2r": ("ONE WAY, upright, arrow right", "MUTCD 2B.40; Table 2B-1: 24 x 30 in", lambda: r6_2("r")),
    "r5-1": ("DO NOT ENTER", "MUTCD 2B.37; Table 2B-1: 30 x 30 in", r5_1),
    "r2-1_25": ("SPEED LIMIT 25", "MUTCD 2B.13; Table 2B-1: 24 x 30 in", lambda: r2_1(25)),
    "r2-1_30": ("SPEED LIMIT 30", "MUTCD 2B.13; Table 2B-1: 24 x 30 in", lambda: r2_1(30)),
    "r2-1_35": ("SPEED LIMIT 35", "MUTCD 2B.13; Table 2B-1: 24 x 30 in", lambda: r2_1(35)),
    "r3-1": ("No right turn", "MUTCD 2B.18; Table 2B-1: 24 x 24 in", lambda: r3_turn("r")),
    "r3-2": ("No left turn", "MUTCD 2B.18; Table 2B-1: 24 x 24 in", lambda: r3_turn("l")),
    "r3-4": ("No U-turn", "MUTCD 2B.18; Table 2B-1: 24 x 24 in", r3_4),
    "r3-5l": ("Left turn ONLY (mandatory movement)", "MUTCD 2B.20; Table 2B-1: 30 x 36 in", lambda: r3_5("l")),
    "r3-5r": ("Right turn ONLY (mandatory movement)", "MUTCD 2B.20; Table 2B-1: 30 x 36 in", lambda: r3_5("r")),
    "r3-5a": ("Through ONLY (mandatory movement)", "MUTCD 2B.20; Table 2B-1: 30 x 36 in", lambda: r3_5("a")),
    "r3-6l": ("Through or left (optional movement)", "MUTCD 2B.21; Table 2B-1: 30 x 36 in", lambda: r3_6("l")),
    "r3-6r": ("Through or right (optional movement)", "MUTCD 2B.21; Table 2B-1: 30 x 36 in", lambda: r3_6("r")),
    "r3-7l": ("LEFT LANE MUST TURN LEFT", "MUTCD 2B.20; Table 2B-1: 30 x 30 in", lambda: r3_7("l")),
    "r3-7r": ("RIGHT LANE MUST TURN RIGHT", "MUTCD 2B.20; Table 2B-1: 30 x 30 in", lambda: r3_7("r")),
    "r3-8_lt": ("Advance lane control: left-turn-only lane, through lane", "MUTCD 2B.22; Table 2B-1: 30 x 30 in", lambda: r3_8("lt")),
    "r3-8_tr": ("Advance lane control: through lane, right-turn-only lane", "MUTCD 2B.22; Table 2B-1: 30 x 30 in", lambda: r3_8("tr")),
    "r3-11_bus": ("RIGHT LANE BUS ONLY", "after the MUTCD R3-11 preferential-lane series (2G.03); legend and 24 x 30 in size are a "
                  "GUESS at what Denver posts on its bus lanes [unverified]", r3_11_bus),
    "r10-3": ("Push button for walk signal", "MUTCD 2B.52; Table 2B-1: 9 x 12 in", r10_3),
    "r15-1_railroad": ("Crossbuck blade RAIL ROAD (the under blade)", "MUTCD 8B.03: two 48 x 9 in blades", lambda: r15_1("railroad")),
    "r15-1_crossing": ("Crossbuck blade CROSSING (the over blade)", "MUTCD 8B.03: two 48 x 9 in blades", lambda: r15_1("crossing")),
    "w10-1": ("Railroad crossing advance warning", "MUTCD 8B.06; Table 8B-1: 36 in disc", w10_1),
    "w11-2": ("Pedestrian crossing, yellow", "MUTCD 2C.50; Table 2C-2: 30 x 30 in diamond", lambda: w11_2(YELLOW)),
    "w11-2_fyg": ("Pedestrian crossing, fluorescent yellow-green", "MUTCD 2C.50 (the optional colour); 30 x 30 in diamond", lambda: w11_2(FYG)),
}


def plate_key(c: Canvas) -> str:
    if c.shape == "rect":
        return f"rect_{c.w:g}x{c.h:g}"
    side = 30 if c.shape == "diamond" else c.w
    return f"{c.shape}_{side:g}"


def plate(c: Canvas) -> Model:
    key = plate_key(c)
    m = Model(f"sign_plate_{key}", f"sign plate cut to the outline, {c.w:.4g} x {c.h:.4g} in bounding rectangle",
              "metres, +y up, origin = the plate's centre, FACE looks along +z; UV 0..1 = the bounding rectangle", MAKER)
    pts = [((x - c.w / 2) * IN, (c.h / 2 - y) * IN) for x, y in outline(c.shape, c.w, c.h)]
    uv = tuple((x / (c.w * IN) + 0.5, y / (c.h * IN) + 0.5) for x, y in pts)
    m.obj("FACE", "SIGNFACE").polygon([(x, y, 0.002) for x, y in pts], uv, (0.0, 0.0, 1.0))
    m.obj("BACK", "SIGNBACK").polygon([(x, y, 0.0) for x, y in pts], uv, (0.0, 0.0, -1.0))
    return m


def build():
    """every face drawn once: ({code: Canvas}, {street: Canvas})"""
    return {code: fn() for code, (_, _, fn) in FACES.items()}, {s: blade(s) for s in DENVER_STREETS}


def spec(faces, blades, plates) -> dict:
    def row(c, **kw):
        return {**kw, "size_in": [round(c.w, 3), round(c.h, 3)], "size_m": [round(c.w * IN, 4), round(c.h * IN, 4)], "shape": c.shape,
                "texture_px": list(c.size), "plate": f"sign_plate_{plate_key(c)}.obj"}
    return {
        "name": "sign_faces",
        "_doc": "ledger 0096 — MUTCD regulatory / warning faces and Denver street-name blades, generated by tools/make_sign_faces.py. "
                "Nothing here is placed on a track.",
        "uv_layout": "the texture is the sign's bounding rectangle edge to edge: u 0..1 left to right, v 0..1 bottom to top, as the "
                     "reader sees it; resampled to a power of two each way (texels not square); alpha 0 outside the outline with the "
                     "face's edge colour bled under it. The sign_plate_*.obj meshes carry exactly these UVs on object FACE.",
        "needs_from_engine": "sign plates must keep their UVs through the prep (PLAN §4b engine work 8); a pbr.TEXTURES row per face "
                             "(or one per material class with a per-face texture) and SIGNBACK -> solid_metal_grey.png; alpha test "
                             "only if a rectangle is used where the outline is not one",
        "accuracy": "sizes are the MUTCD's single-lane conventional-road sizes (scale the plate where Table 2B-1 gives the larger "
                    "multi-lane size); layouts are drawn from knowledge of the standard signs, not measured off the Standard Highway "
                    "Signs sheets; the letters approximate the FHWA Standard Alphabets",
        "mounting": {"bottom_above_walk_m": round(7 * 0.3048, 4), "from_kerb_face_m": round(2 * 0.3048, 4), "source": "MUTCD 2A.18, 2A.19"},
        "faces": {code: row(c, file=f"mutcd_{code}.png", title=FACES[code][0], reference=FACES[code][1]) for code, c in faces.items()},
        "blades": {"_doc": "Denver street-name blades, in tracks/denver-grand-prix/textures/blades/. Style (green, white capitals, small "
                           "prefix and suffix) is from memory and UNVERIFIED. 36 x 9 in is a [typical] post-mounted blade; the same "
                           "4:1 texture serves an overhead mast-arm name sign (72 x 18 in) by scaling the plate.",
                   "streets": {s: row(c, file=blade_file(s), legend=list(blade_legend(s))) for s, c in blades.items()}},
        "plates": {n[:-4]: m.summary() for n, m in plates.items()},
    }


def outputs():
    faces, blades = build()
    plates = {}
    for c in list(faces.values()) + list(blades.values()):
        m = plate(c)
        plates.setdefault(m.name + ".obj", m)
    text = {n: m.text() for n, m in sorted(plates.items())}
    text["sign_faces.json"] = json.dumps(spec(faces, blades, dict(sorted(plates.items()))), indent=1) + "\n"
    return text, {f"mutcd_{code}.png": c.image() for code, c in faces.items()}, {blade_file(s): c.image() for s, c in blades.items()}


def main(argv: list[str]) -> int:
    from street_furniture_draw import write_or_check_png
    text, face_png, blade_png = outputs()
    return (write_or_check(OUT, text, argv, "sign-faces") | write_or_check_png(TEX, face_png, argv, "sign-faces")
            | write_or_check_png(BLADES, blade_png, argv, "sign-faces"))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

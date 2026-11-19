"""Generate the bespoke (self-made, CC0) dressing assets — .claude/skills/bespoke-assets, first batch: Nevada Nights.

Nothing here is captured or mined: every pixel and vertex comes from this script (seeded generators, Pillow only), so
rerunning reproduces the files byte for byte under the same Pillow.

  assets/textures/fabric_white_diffuse.jpg, _normal.jpg   white PVC tent fabric, one tile = FABRIC_BAY_M x FABRIC_BAY_M,
                                                          a welded panel seam at u = 0. pbr row BUILDING_FABRIC
  assets/textures/traffic_cone_diffuse.png                the cone's strip: v = 0..PLATE_V the black base, then orange
                                                          with the two white bands. pbr row PROPCONE
  assets/textures/desert_scrub_atlas.png                  2 x 2 alpha cutout: creosote, creosote, bursage, bursage. pbr
                                                          row SCRUBCARD (BILLBOARD: ksTree, alpha test)
  assets/models/traffic_cone.obj, traffic_cone.json       the cone, base at y = 0, +y up, 37 vertices

The second batch (all chain tracks, 2026-10-31):
  assets/textures/tiltup_wall_diffuse.jpg, _normal.jpg    tilt-up concrete, one tile = PANEL_BAY_M, a panel joint. pbr rows
                                                          BUILDING_TILTUP, 1WALL_TILTUP
  assets/textures/metal_wall_diffuse.jpg, _normal.jpg     ribbed steel siding, one tile = METAL_BAY_M. pbr row BUILDING_METAL
  assets/textures/roof_{white,tan,dark}_diffuse.jpg       flat roofs, the three classes read off NAIP. pbr rows ROOFTOP_*
  assets/textures/pad_asphalt_diffuse.jpg                 a parking or paddock pad, plain weathered. pbr row PADAPRON
  assets/textures/wbeam_rail_diffuse.png                  W-beam rail and post. pbr row GUARDRAIL
  assets/textures/ghost_alpha.png                         fully transparent: a collider that stands behind a rail, pbr row 1WALL_GHOST
  assets/textures/deciduous_atlas.png                     2 x 2 cutout: oak, maple, hickory, cottonwood. pbr row TREECARD
  assets/textures/prairie_atlas.png                       2 x 2 cutout: rabbitbrush, soapweed yucca, bunchgrass, snakeweed. pbr row PRAIRIECARD
  assets/textures/tecpro_diffuse.png                     a red and a white module. pbr row 1WALL_TECPRO
  assets/textures/krail_bluewhite_diffuse.png             a blue and a white K-rail section. pbr row 1WALL_KRAILBW
  assets/textures/tyre_wall_diffuse.png                   two stacked-tyre columns, five tyres up (ledger 0082). Bound per
                                                          track by texture_overrides["1WALL_TECPRO"] (Milford)
  assets/textures/drystone_diffuse.jpg, _normal.jpg       laid dry stone, one tile = 2 m. pbr row BUILDING_DRYSTONE
  assets/textures/conifer_foothill_atlas.png              2 x 2 cutout: ponderosa, Douglas-fir, juniper, mahogany. pbr row TREECARD_CONIFER
  assets/textures/stucco_wall_diffuse.jpg, _normal.jpg    a house bay with its window, tan stucco. pbr row BUILDING_STUCCO
  assets/textures/siding_wall_diffuse.jpg, _normal.jpg    the same bay in white lap siding. pbr row BUILDING_SIDING
  assets/textures/shingle_roof_diffuse.jpg                asphalt shingle, one tile = 2 m. pbr row ROOFTOP_SHINGLE

The third batch (circuit buildings, ledger 0094, 2026-11-18; numpy, tools/circuit_facades.py's cell table):
  assets/textures/circuit_facade_diffuse.jpg, _normal.jpg the facade atlas: 16 cells of one bay x one module each, ribbed
                                                          metal (plain, roll-up door, man door + window, window band), tilt-up
                                                          (plain panel, dock door, man door + louvre, louvre + downspout),
                                                          corrugated containers (white / tan / blue sides and door ends), a
                                                          rooftop unit's side, two grime bands. Bound by a track's
                                                          texture_overrides on BUILDING_/FARBLOCK_METAL / _TILTUP
  assets/textures/roof_membrane_normal.jpg                a single-ply membrane's laps and fasteners, 12 m a tile (ROOFTOP_*)
  assets/textures/roof_rib_normal.jpg                     ribbed metal roofing, 12 m a tile (ROOFTOP_*)
  assets/textures/fabric_tent_diffuse.jpg, _normal.jpg    a clearspan tent's panel with its frame's keder and creases (BUILDING_FABRIC)

    PYTHONUTF8=1 python tools/make_bespoke_assets.py --only circuit    # writes the third batch alone

DIMENSIONS:
  cone height      0.71 m (28 in)   MUTCD Part 6, channelizing cones: at least 28 in where speeds are high; cited from
                                    memory, not re-read
  cone bands       6 in white 4 in from the top, 4 in white 2 in below it (the same section, for cones of 28 in and
                                    over; cited from memory, not re-read)
  cone base        0.356 m square (14 in), the common plate of a 28 in cone [invented: no standard fixes it]
  fabric bay       5 m              the usual bay of a clearspan frame tent [invented]; the imagery does not resolve it
  creosote         the cards are sized by the author tool from the clumps measured on NAIP (track.config.json
                   scenery.bespoke.scrub); the drawings only keep the plants' habits: creosote open and multi-stemmed with
                   small dark olive leaves, bursage a low rounded grey mound (DOSSIER section 6, USDA ESD R030XB005NV)
  tilt-up panel    8 m bay          a common panel width [invented]
  steel rib        0.914 m bay      36 in cover width of R-panel siding (cited from memory, not re-read)
  W-beam           the rail's own numbers live in tools/author_bespoke_blend.py; this strip is its skin
  tree species     DOSSIER Part D section 6 (oak, hickory, maple) on Milford; cottonwood on the Sand Creek bottoms [regional
                   knowledge, not measured]. High Plains' four plants are shortgrass-prairie regulars [regional knowledge]

    PYTHONUTF8=1 python tools/make_bespoke_assets.py            # writes the files
    PYTHONUTF8=1 python tools/make_bespoke_assets.py --check    # exit 1 if the committed files differ
"""
from __future__ import annotations

import hashlib
import json
import math
import random
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps, ImageStat

AIROSO = Path(__file__).resolve().parents[1]
TEX = AIROSO / "assets" / "textures"
MODELS = AIROSO / "assets" / "models"

FABRIC_BAY_M = 5.0
FABRIC_N = 512
FABRIC_SEED = 20130928            # the NAIP date the two tents are measured from
CONE_H = 28 * 0.0254              # 0.7112 m
CONE_BASE = 14 * 0.0254           # 0.3556 m square
CONE_R0, CONE_R1 = 0.125, 0.030   # body radius at the plate and at the top [invented: a typical 28 in cone]
CONE_PLATE_H = 0.025              # [invented]
CONE_SIDES = 8
BAND_TOP = (4 * 0.0254, 6 * 0.0254)    # from the top: gap, band
BAND_LOW = (2 * 0.0254, 4 * 0.0254)    # below the first band: gap, band
PLATE_V = 0.06
ATLAS_N = 1024
ATLAS_SEED = 20261031
PANEL_BAY_M = 8.0
METAL_BAY_M = 0.914
WALL_N = 512
ROOF_N = 256
TREE_ATLAS_N = 2048
HOUSE_BAY_M = 3.0                 # one window per bay [invented]; tools/author_bespoke_blend.py TILE_BAY
HOUSE_FLOOR_M = 3.0               # the tile is square: one bay by one floor
SHINGLE_TILE_M = 2.0


def _noise(rng, n, small, blur):
    """a tileable grey field: a seeded small grid tiled 3x3, enlarged, blurred, the centre kept"""
    s = Image.frombytes("L", (small, small), bytes(rng.randrange(256) for _ in range(small * small)))
    t = Image.new("L", (3 * small, 3 * small))
    for a in range(3):
        for b in range(3):
            t.paste(s, (a * small, b * small))
    t = t.resize((3 * n, 3 * n), Image.BICUBIC).filter(ImageFilter.GaussianBlur(blur))
    return ImageOps.autocontrast(t.crop((n, n, 2 * n, 2 * n)), cutoff=1)


def _normal_from_height(h, strength):
    """height -> OpenGL normal (+y = up the image), wrapping at the edges"""
    n = h.width
    hp = h.load()
    out = Image.new("RGB", (n, n))
    op = out.load()
    for y in range(n):
        yu, yd = (y - 1) % n, (y + 1) % n
        for x in range(n):
            xl, xr = (x - 1) % n, (x + 1) % n
            dx = (hp[xr, y] - hp[xl, y]) / 255.0 * strength
            dy = (hp[x, yd] - hp[x, yu]) / 255.0 * strength
            ln = math.sqrt(dx * dx + dy * dy + 1.0)
            op[x, y] = (int(127.5 - dx / ln * 127.5), int(127.5 + dy / ln * 127.5), int(127.5 + 127.5 / ln))
    return out


def fabric(out_dir: Path) -> None:
    """off-white PVC panel: a faint weave of blotches and sag, darker along the welded seam at u = 0"""
    n = FABRIC_N
    rng = random.Random(FABRIC_SEED)
    blotch = _noise(rng, n, 8, 28)
    fine = _noise(rng, n, 128, 1.0)
    seam = Image.new("L", (n, n), 0)
    d = ImageDraw.Draw(seam)
    d.rectangle((0, 0, 3, n), fill=255)
    d.rectangle((n - 3, 0, n, n), fill=255)
    seam = seam.filter(ImageFilter.GaussianBlur(1.2))
    grey = Image.blend(blotch, fine, 0.35).point(lambda v: 226 + v * 22 // 255)
    img = Image.merge("RGB", (grey, grey, grey.point(lambda v: max(0, v - 6))))
    img = ImageChops.multiply(img, Image.merge("RGB", [seam.point(lambda v: 255 - v * 70 // 255)] * 3))
    img.save(out_dir / "fabric_white_diffuse.jpg", quality=90, optimize=True)
    h = ImageChops.add(blotch.point(lambda v: v // 3), seam.point(lambda v: v // 2))
    _normal_from_height(h.filter(ImageFilter.GaussianBlur(1.0)), 2.0).save(
        out_dir / "fabric_white_normal.jpg", quality=90, optimize=True)


def cone_texture(out_dir: Path) -> None:
    """a 16 x 256 strip, v up the cone: black plate, orange body, the two white bands"""
    w, h = 16, 256
    img = Image.new("RGB", (w, h), (232, 84, 18))
    d = ImageDraw.Draw(img)

    def row(height_m):            # a height on the cone -> a pixel row (v = 1 is row 0)
        v = PLATE_V + (1.0 - PLATE_V) * height_m / CONE_H
        return int(round((1.0 - v) * h))
    t0 = CONE_H - BAND_TOP[0]
    t1 = t0 - BAND_TOP[1]
    l0 = t1 - BAND_LOW[0]
    l1 = l0 - BAND_LOW[1]
    d.rectangle((0, row(t0), w, row(t1)), fill=(238, 238, 232))
    d.rectangle((0, row(l0), w, row(l1)), fill=(238, 238, 232))
    d.rectangle((0, row(0.0), w, h), fill=(24, 24, 26))
    img.save(out_dir / "traffic_cone_diffuse.png", optimize=True)


def cone_model(out_dir: Path) -> None:
    """base plate (a flat square slab) + an 8-sided tapered body; OBJ frame +y up, base at y = 0"""
    verts, uvs, faces = [], [], []

    def add(p, uv):
        verts.append(p)
        uvs.append(uv)
        return len(verts)
    b = CONE_BASE / 2
    plate_uv = (0.5, PLATE_V / 2)
    corners = ((-b, -b), (b, -b), (b, b), (-b, b))
    low = [add((x, 0.0, z), plate_uv) for x, z in corners]
    top = [add((x, CONE_PLATE_H, z), plate_uv) for x, z in corners]
    faces.append((0, top))                                                    # up
    for k in range(4):
        faces.append((0, [low[k], low[(k + 1) % 4], top[(k + 1) % 4], top[k]][::-1]))
    # the body: stations round the cone, the seam vertex repeated so u closes at 1
    ring0, ring1 = [], []
    for k in range(CONE_SIDES + 1):
        a = 2 * math.pi * k / CONE_SIDES
        u = k / CONE_SIDES
        ring0.append(add((CONE_R0 * math.cos(a), CONE_PLATE_H, CONE_R0 * math.sin(a)), (u, PLATE_V)))
        ring1.append(add((CONE_R1 * math.cos(a), CONE_H, CONE_R1 * math.sin(a)), (u, 1.0)))
    for k in range(CONE_SIDES):
        faces.append((1, [ring0[k], ring1[k], ring1[k + 1], ring0[k + 1]]))
    cap = add((0.0, CONE_H, 0.0), (0.5, 1.0))
    for k in range(CONE_SIDES):
        faces.append((0, [ring1[k], cap, ring1[k + 1]]))
    lines = ["# traffic cone, generated by tools/make_bespoke_assets.py (CC0). Metres, +y up, base at y = 0.", "o PROPCONE"]
    lines += [f"v {x:.4f} {y:.4f} {z:.4f}" for x, y, z in verts]
    lines += [f"vt {u:.4f} {v:.4f}" for u, v in uvs]
    cur = None
    for g, f in faces:
        if g != cur:
            lines.append("s off" if g == 0 else f"s {g}")
            cur = g
        lines.append("f " + " ".join(f"{i}/{i}" for i in f))
    (out_dir / "traffic_cone.obj").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    spec = {"name": "traffic_cone", "height_m": round(CONE_H, 4), "base_m": round(CONE_BASE, 4),
            "footprint_radius_m": round(b * math.sqrt(2), 4), "file": "traffic_cone.obj", "vertices": len(verts),
            "generator": "tools/make_bespoke_assets.py"}
    (out_dir / "traffic_cone.json").write_text(json.dumps(spec, indent=1) + "\n", encoding="utf-8", newline="\n")


def _shrub(rng, cell, height, width, stem_col, leaves, clusters, per_cluster, leaf_r, sigma):
    """one plant on its own transparent cell (so nothing crosses into a neighbour), standing on the cell's bottom edge: a
    dome of leaf clusters, each on a thin stem from the crown, as both plants read from a car"""
    img = Image.new("RGBA", (cell, cell), (*leaves[0][:3], 0))
    d = ImageDraw.Draw(img)
    cx, base = cell / 2, cell - 2
    spots = []
    for _ in range(clusters):
        th = rng.uniform(0.08, math.pi - 0.08)
        r = math.sqrt(rng.uniform(0.15, 1.0))
        spots.append((cx + math.cos(th) * r * (width / 2 - sigma), base - math.sin(th) * r * (height - sigma)))
    for x, y in spots:
        d.line((cx + (x - cx) * 0.12, base, x, y), fill=stem_col, width=2)
    spots.sort(key=lambda q: q[1])
    for x, y in spots:
        for _ in range(per_cluster):
            lr = rng.uniform(leaf_r * 0.6, leaf_r * 1.3)
            lx, ly = x + rng.gauss(0, sigma), y + rng.gauss(0, sigma)
            d.ellipse((lx - lr, ly - lr, lx + lr, ly + lr), fill=leaves[rng.randrange(len(leaves))])
    return img


def scrub_atlas(out_dir: Path) -> None:
    """2 x 2 cells: creosote (top row: open, a little taller than wide), bursage (bottom row: a low wide mound); the
    transparent ground keeps the leaf colour in RGB so a mip never halos"""
    n = ATLAS_N
    cell = n // 2
    rng = random.Random(ATLAS_SEED)
    img = Image.new("RGBA", (n, n), (86, 88, 58, 0))
    creosote = [(70, 78, 40, 255), (84, 92, 48, 255), (60, 68, 36, 255), (98, 102, 58, 255)]
    bursage = [(150, 146, 118, 255), (132, 130, 100, 255), (166, 160, 130, 255), (118, 116, 90, 255)]
    for row in range(2):
        for col in range(2):
            if row == 0:
                p = _shrub(rng, cell, cell * 0.94, cell * 0.86, (64, 56, 48, 255), creosote, 34, 34, 3.0, 17)
            else:
                p = _shrub(rng, cell, cell * 0.62, cell * 0.92, (104, 96, 82, 255), bursage, 40, 46, 3.4, 20)
            img.paste(p, (col * cell, row * cell))
    img.save(out_dir / "desert_scrub_atlas.png", optimize=True)


def tiltup(out_dir: Path) -> None:
    """weathered concrete, a vertical joint at u = 0; the blotches are the panel's cure and weather"""
    n = WALL_N
    rng = random.Random(8080)
    blotch = _noise(rng, n, 6, 34)
    fine = _noise(rng, n, 160, 0.8)
    joint = Image.new("L", (n, n), 0)
    d = ImageDraw.Draw(joint)
    d.rectangle((0, 0, 2, n), fill=255)
    d.rectangle((n - 2, 0, n, n), fill=255)
    grey = Image.blend(blotch, fine, 0.3).point(lambda v: 150 + v * 42 // 255)
    img = Image.merge("RGB", (grey.point(lambda v: min(255, v + 5)), grey.point(lambda v: min(255, v + 2)), grey.point(lambda v: max(0, v - 5))))
    img = ImageChops.multiply(img, Image.merge("RGB", [joint.point(lambda v: 255 - v * 130 // 255)] * 3))
    img.save(out_dir / "tiltup_wall_diffuse.jpg", quality=88, optimize=True)
    h = ImageChops.add(fine.point(lambda v: v // 5), joint.point(lambda v: 255 - v).point(lambda v: v // 2))
    _normal_from_height(h.filter(ImageFilter.GaussianBlur(0.7)), 1.5).save(out_dir / "tiltup_wall_normal.jpg", quality=88, optimize=True)


def metal(out_dir: Path) -> None:
    """R-panel siding, one rib bay per tile: a pale grey with the rib's shadow at u = 0.5"""
    n = WALL_N
    rng = random.Random(914)
    fine = _noise(rng, n, 64, 3)
    prof = [int(232 - 92 * math.exp(-((x - n / 2) / (n * 0.045)) ** 2) - 16 * math.exp(-((x - n / 4) / (n * 0.03)) ** 2)
                - 16 * math.exp(-((x - 3 * n / 4) / (n * 0.03)) ** 2)) for x in range(n)]
    col = Image.new("L", (n, 1))
    col.putdata(prof)
    col = col.resize((n, n))
    grey = ImageChops.multiply(col, fine.point(lambda v: 232 + v * 23 // 255))
    Image.merge("RGB", (grey, grey, grey.point(lambda v: min(255, v + 3)))).save(out_dir / "metal_wall_diffuse.jpg", quality=88, optimize=True)
    _normal_from_height(col, 3.0).save(out_dir / "metal_wall_normal.jpg", quality=88, optimize=True)


def roofs(out_dir: Path) -> None:
    """three flat-roof tiles, near the classes the buildings are sorted into on NAIP (tools/plan_buildings.py)"""
    rng = random.Random(4242)
    for name, c in (("white", (222, 222, 216)), ("tan", (168, 146, 112)), ("dark", (84, 86, 90))):
        n = ROOF_N
        f = Image.blend(_noise(rng, n, 5, 22), _noise(rng, n, 96, 0.8), 0.45).point(lambda v: 222 + v * 33 // 255)
        ImageChops.multiply(Image.new("RGB", (n, n), c), Image.merge("RGB", (f, f, f))).save(out_dir / f"roof_{name}_diffuse.jpg", quality=86, optimize=True)


def pad(out_dir: Path) -> None:
    """a plain aged parking pad: lighter and quieter than a track surface, with tar streaks"""
    n = WALL_N
    rng = random.Random(1999)
    f = Image.blend(_noise(rng, n, 6, 30), _noise(rng, n, 200, 0.7), 0.6).point(lambda v: 74 + v * 40 // 255)
    img = Image.merge("RGB", (f, f, f.point(lambda v: max(0, v - 3))))
    d = ImageDraw.Draw(img)
    for _ in range(14):
        x, y = rng.uniform(0, n), rng.uniform(0, n)
        pts = [(x, y)]
        for _ in range(5):
            x += rng.uniform(-50, 50)
            y += rng.uniform(-50, 50)
            pts.append((x, y))
        d.line(pts, fill=(46, 46, 46), width=2)
    img.filter(ImageFilter.GaussianBlur(0.5)).save(out_dir / "pad_asphalt_diffuse.jpg", quality=88, optimize=True)


def wbeam(out_dir: Path) -> None:
    """galvanised steel: u along one 3.81 m panel with its splice bolts at u = 0, v across the rail; the post uses the same strip"""
    w, h = 256, 64
    rng = random.Random(381)
    f = _noise(rng, 256, 64, 2).resize((w, h)).point(lambda v: 186 + v * 40 // 255)
    img = Image.merge("RGB", (f, f, f.point(lambda v: min(255, v + 4))))
    d = ImageDraw.Draw(img)
    for x in (2, 6):
        for y in (14, 28, 36, 50):
            d.ellipse((x, y, x + 2, y + 2), fill=(70, 70, 72))
    img.save(out_dir / "wbeam_rail_diffuse.png", optimize=True)


def ghost(out_dir: Path) -> None:
    Image.new("RGBA", (4, 4), (128, 128, 128, 0)).save(out_dir / "ghost_alpha.png", optimize=True)


def _tree(rng, cell, crown_w, crown_h, crown_y, trunk_col, leaves, clumps, per_clump, leaf_r, spread):
    """one tree standing on the cell's bottom edge: a trunk up into a crown of overlapping leaf clumps, darker low and to one
    side, so a card reads as a mass with a lit top. crown_y = the crown's centre height, in px above the base"""
    img = Image.new("RGBA", (cell, cell), (*leaves[0][:3], 0))
    d = ImageDraw.Draw(img)
    cx, base = cell / 2, cell - 2
    tw = max(4, int(cell * 0.022))
    d.polygon([(cx - tw * 1.4, base), (cx + tw * 1.4, base), (cx + tw * 0.6, base - crown_y), (cx - tw * 0.6, base - crown_y)], fill=trunk_col)
    for _ in range(9):
        a = rng.uniform(math.pi * 0.15, math.pi * 0.85)
        ln = rng.uniform(0.3, 0.8)
        y0 = base - crown_y * rng.uniform(0.5, 1.0)
        d.line((cx, y0, cx + math.cos(a) * crown_w * 0.5 * ln, y0 - math.sin(a) * crown_h * 0.45 * ln), fill=trunk_col, width=max(2, tw // 2))
    spots = []
    for _ in range(clumps):
        th = rng.uniform(0, 2 * math.pi)
        r = math.sqrt(rng.random())
        spots.append((cx + math.cos(th) * r * crown_w / 2 * 0.86, base - crown_y + math.sin(th) * r * crown_h / 2 * 0.86))
    spots.sort(key=lambda q: -q[1])          # low clumps first, the lit upper ones on top
    for x, y in spots:
        lift = (base - crown_y + crown_h / 2 - y) / crown_h           # 0 at the crown's foot, 1 at its top
        side = (x - cx) / crown_w + 0.5
        shade = min(len(leaves) - 1, int((lift * 0.75 + side * 0.25) * len(leaves)))
        for _ in range(per_clump):
            lr = rng.uniform(leaf_r * 0.5, leaf_r * 1.25)
            lx, ly = x + rng.gauss(0, spread), y + rng.gauss(0, spread)
            lx = min(cell - lr - 1, max(lr + 1, lx))
            ly = max(lr + 1, ly)
            pick = leaves[max(0, min(len(leaves) - 1, shade + rng.randrange(-1, 2)))]
            d.ellipse((lx - lr, ly - lr, lx + lr, ly + lr), fill=pick)
    return img


def deciduous_atlas(out_dir: Path) -> None:
    """top row oak, maple; bottom row hickory, cottonwood. Each ramp runs from the shaded underside to the lit top"""
    n = TREE_ATLAS_N
    c = n // 2
    rng = random.Random(ATLAS_SEED + 1)
    img = Image.new("RGBA", (n, n), (56, 76, 38, 0))
    bark = (62, 52, 42, 255)
    oak = [(30, 46, 22, 255), (40, 60, 28, 255), (52, 74, 34, 255), (68, 90, 42, 255), (84, 106, 52, 255)]
    maple = [(32, 52, 26, 255), (44, 68, 32, 255), (58, 84, 38, 255), (76, 102, 46, 255), (94, 120, 56, 255)]
    hick = [(34, 48, 24, 255), (46, 62, 30, 255), (60, 78, 36, 255), (78, 94, 44, 255), (96, 110, 54, 255)]
    cott = [(44, 58, 30, 255), (60, 76, 38, 255), (78, 94, 46, 255), (98, 112, 56, 255), (120, 130, 70, 255)]
    specs = ((0, 0, oak, c * 0.96, c * 0.72, c * 0.58), (0, 1, maple, c * 0.82, c * 0.80, c * 0.56),
             (1, 0, hick, c * 0.62, c * 0.86, c * 0.54), (1, 1, cott, c * 0.84, c * 0.84, c * 0.54))
    for row, col, leaves, w, h, y in specs:
        t = _tree(rng, c, w, h, y, bark, leaves, 150, 40, c * 0.0075, c * 0.03)
        img.paste(t, (col * c, row * c))
    img.save(out_dir / "deciduous_atlas.png", optimize=True)


def prairie_atlas(out_dir: Path) -> None:
    """rabbitbrush (grey-green dome, straw tips), soapweed yucca (a spiky rosette), bunchgrass (a straw tuft), snakeweed (a low
    yellow-green mound)"""
    n = ATLAS_N
    c = n // 2
    rng = random.Random(ATLAS_SEED + 2)
    img = Image.new("RGBA", (n, n), (130, 124, 84, 0))
    img.paste(_shrub(rng, c, c * 0.86, c * 0.9, (90, 84, 66, 255), [(112, 122, 92, 255), (130, 138, 104, 255), (96, 106, 82, 255), (170, 158, 92, 255)], 40, 40, 3.2, 18), (0, 0))
    y = Image.new("RGBA", (c, c), (86, 104, 60, 0))
    d = ImageDraw.Draw(y)
    cx, base = c / 2, c - 2
    for _ in range(120):
        a = rng.uniform(math.pi * 0.07, math.pi * 0.93)
        ln = rng.uniform(0.5, 1.0) * c * 0.88
        tip = (cx + math.cos(a) * ln * 0.55, base - math.sin(a) * ln)
        wid = rng.uniform(4, 8)
        col = rng.choice([(78, 100, 56, 255), (96, 118, 66, 255), (64, 84, 48, 255), (120, 130, 80, 255)])
        d.polygon([(cx - wid, base), (cx + wid, base), tip], fill=col)
    img.paste(y, (c, 0))
    b = Image.new("RGBA", (c, c), (168, 150, 100, 0))
    d = ImageDraw.Draw(b)
    for _ in range(420):
        x0 = cx + rng.gauss(0, c * 0.1)
        lean = rng.uniform(-0.45, 0.45)
        ln = rng.uniform(0.45, 0.95) * c * 0.92
        col = rng.choice([(176, 156, 104, 255), (156, 138, 90, 255), (192, 172, 120, 255), (136, 124, 80, 255)])
        d.line((x0, base, x0 + lean * ln * 0.5, base - ln * 0.6, x0 + lean * ln, base - ln), fill=col, width=2)
    img.paste(b, (0, c))
    img.paste(_shrub(rng, c, c * 0.55, c * 0.92, (110, 100, 70, 255), [(140, 146, 76, 255), (160, 158, 84, 255), (122, 130, 68, 255), (186, 172, 88, 255)], 40, 46, 3.0, 20), (c, c))
    img.save(out_dir / "prairie_atlas.png", optimize=True)


def tecpro(out_dir: Path) -> None:
    """one Tec-Pro skin for a pair of modules: u 0..0.5 red, 0.5..1 white, a seam at the top and foot of each"""
    n = 256
    img = Image.new("RGB", (n, n), (176, 38, 34))
    d = ImageDraw.Draw(img)
    d.rectangle((n // 2, 0, n, n), fill=(226, 224, 218))
    rng = random.Random(1200)
    wear = _noise(rng, n, 32, 2).point(lambda v: 214 + v * 41 // 255)
    img = ImageChops.multiply(img, Image.merge("RGB", (wear, wear, wear)))
    d = ImageDraw.Draw(img)
    for y in (0, 1, n // 2, n - 2, n - 1):
        d.line((0, y, n, y), fill=(52, 50, 48))
    img.save(out_dir / "tecpro_diffuse.png", optimize=True)


def krail(out_dir: Path) -> None:
    """a pair of K-rail sections for one skin: u 0..0.5 blue, 0.5..1 white, as High Plains paints them on NAIP 2023; scuffed"""
    n = 256
    img = Image.new("RGB", (n, n), (46, 104, 168))
    d = ImageDraw.Draw(img)
    d.rectangle((n // 2, 0, n, n), fill=(226, 228, 228))
    rng = random.Random(810)
    wear = _noise(rng, n, 24, 2).point(lambda v: 196 + v * 59 // 255)
    img = ImageChops.multiply(img, Image.merge("RGB", (wear, wear, wear)))
    d = ImageDraw.Draw(img)
    d.rectangle((0, n - 16, n, n), fill=(82, 80, 76))
    img.save(out_dir / "krail_bluewhite_diffuse.png", optimize=True)


def tyre_wall(out_dir: Path) -> None:
    """a stacked-tyre wall's skin for a pair of module columns (u 0..0.5, 0.5..1: one tyre each, 0.62 m), five tyres up the
    tile (v 0..1 = the 1.0 m wall [invented]); treads facing out, each tyre's shoulders darker than its crown, a black gap
    between tyres; ledger 0082 (Milford's tyre walls are black on NAIP 2022)"""
    n = 256
    rng = random.Random(620)
    img = Image.new("RGB", (n, n), (20, 20, 21))
    d = ImageDraw.Draw(img)
    band = n // 5
    for col in (0, n // 2):
        for t in range(5):
            y0, y1 = t * band + 3, (t + 1) * band - 3
            for y in range(y0, y1):
                k = abs((y - (y0 + y1) / 2) / ((y1 - y0) / 2))          # 0 at the crown, 1 at a shoulder
                g = int(46 - 18 * k * k)
                d.line((col + 2, y, col + n // 2 - 3, y), fill=(g, g, g + 1))
            for x in range(col + 4, col + n // 2 - 4, 7):                # tread blocks
                d.line((x, y0 + 6, x + 3, y1 - 6), fill=(30, 30, 31))
    wear = _noise(rng, n, 32, 2).point(lambda v: 205 + v * 50 // 255)
    img = ImageChops.multiply(img, Image.merge("RGB", (wear, wear, wear)))
    img.save(out_dir / "tyre_wall_diffuse.png", optimize=True)


def drystone(out_dir: Path) -> None:
    """laid dry stone (Lariat DOSSIER section 5a: the 1917 walls and pylons): coursed rough blocks with dark joints, tan and
    grey-brown, one tile = 2 m. Drawn, no photograph: ledger 0005, the stone_tan source is not recorded"""
    n = 1024
    rng = random.Random(1917)
    base = Image.new("RGB", (n, n), (40, 36, 30))
    d = ImageDraw.Draw(base)
    height = Image.new("L", (n, n), 0)
    dh = ImageDraw.Draw(height)
    stones = [(148, 128, 102), (132, 112, 88), (160, 142, 116), (118, 102, 84), (138, 122, 104), (112, 92, 72), (168, 150, 124)]
    rows, y = [], 0
    while y < n:
        h = rng.randint(70, 120)
        rows.append((y, min(h, n - y)))
        y += h
    for y, h in rows:
        x = rng.randint(-120, 0)
        while x < n:
            w = rng.randint(90, 220)
            col = stones[rng.randrange(len(stones))]
            for ox in (0, -n, n):
                pts = [(x + ox + rng.uniform(2, 9), y + rng.uniform(2, 8)), (x + ox + w - rng.uniform(2, 9), y + rng.uniform(2, 8)),
                       (x + ox + w - rng.uniform(1, 7), y + h / 2), (x + ox + w - rng.uniform(2, 9), y + h - rng.uniform(2, 8)),
                       (x + ox + rng.uniform(2, 9), y + h - rng.uniform(2, 8)), (x + ox + rng.uniform(1, 7), y + h / 2)]
                d.polygon(pts, fill=col)
                dh.polygon(pts, fill=rng.randint(150, 230))
            x += w
    f = _noise(rng, n, 96, 1.5).point(lambda v: 200 + v * 55 // 255)
    ImageChops.multiply(base, Image.merge("RGB", (f, f, f))).save(out_dir / "drystone_diffuse.jpg", quality=88, optimize=True)
    _normal_from_height(height.filter(ImageFilter.GaussianBlur(2.5)), 3.0).save(out_dir / "drystone_normal.jpg", quality=88, optimize=True)


def _conifer(rng, cell, width, height, tiers, colours, trunk):
    """a tiered conifer on the cell's bottom edge: whorls of drooping needle clumps, narrowing upward"""
    img = Image.new("RGBA", (cell, cell), (*colours[0][:3], 0))
    d = ImageDraw.Draw(img)
    cx, base = cell / 2, cell - 2
    tw = max(3, int(cell * 0.016))
    d.polygon([(cx - tw * 1.3, base), (cx + tw * 1.3, base), (cx, base - height)], fill=trunk)
    for t in range(tiers):
        k = t / max(1, tiers - 1)
        y = base - height * (0.14 + 0.86 * k)
        half = width / 2 * (1 - k) ** 0.85 + cell * 0.012
        shade = colours[min(len(colours) - 1, int(k * len(colours)))]
        for _ in range(int(40 + 90 * (1 - k))):
            x = cx + rng.uniform(-half, half)
            droop = abs(x - cx) * 0.26 + rng.uniform(-cell * 0.018, cell * 0.026)
            r = rng.uniform(cell * 0.006, cell * 0.014)
            c = colours[max(0, min(len(colours) - 1, colours.index(shade) + rng.randrange(-1, 2)))]
            d.ellipse((x - r, y + droop - r, x + r, y + droop + r), fill=c)
    return img


def conifer_atlas(out_dir: Path) -> None:
    """top row ponderosa (open, an orange-brown trunk), Douglas-fir (dense, narrow); bottom row Rocky Mountain juniper (a dark
    irregular mass, short), mountain mahogany (a low grey-green shrub). Lariat DOSSIER section 6, the species it names"""
    n = TREE_ATLAS_N
    c = n // 2
    rng = random.Random(ATLAS_SEED + 3)
    img = Image.new("RGBA", (n, n), (40, 58, 34, 0))
    pond = [(30, 48, 28, 255), (42, 62, 34, 255), (54, 76, 40, 255), (70, 92, 50, 255)]
    doug = [(20, 36, 24, 255), (28, 46, 30, 255), (38, 58, 36, 255), (50, 70, 44, 255)]
    img.paste(_conifer(rng, c, c * 0.62, c * 0.96, 22, pond, (120, 76, 44, 255)), (0, 0))
    img.paste(_conifer(rng, c, c * 0.50, c * 0.97, 34, doug, (70, 54, 42, 255)), (c, 0))
    juni = [(34, 50, 38, 255), (44, 62, 46, 255), (56, 74, 54, 255), (70, 88, 64, 255)]
    img.paste(_tree(rng, c, c * 0.74, c * 0.82, c * 0.5, (82, 66, 50, 255), juni, 120, 34, c * 0.007, c * 0.03), (0, c))
    img.paste(_shrub(rng, c, c * 0.62, c * 0.92, (88, 76, 60, 255), [(96, 110, 80, 255), (110, 122, 90, 255), (82, 94, 70, 255), (124, 132, 100, 255)], 44, 46, 3.2, 20), (c, c))
    img.save(out_dir / "conifer_foothill_atlas.png", optimize=True)


def _window(d, cx, sill, w, h):
    """one window: frame, dark glass, a lit sky reflection band at the top"""
    d.rectangle((cx - w / 2 - 6, sill - h - 6, cx + w / 2 + 6, sill + 6), fill=(236, 236, 230))
    d.rectangle((cx - w / 2, sill - h, cx + w / 2, sill), fill=(38, 46, 56))
    d.rectangle((cx - w / 2, sill - h, cx + w / 2, sill - h * 0.6), fill=(96, 118, 142))
    d.rectangle((cx - 3, sill - h, cx + 3, sill), fill=(226, 226, 220))


def house_walls(out_dir: Path) -> None:
    """one tile = one HOUSE_BAY_M x HOUSE_FLOOR_M bay with a window at a 0.9 m sill, 1.2 x 1.4 m (a common bedroom window; cited
    from memory): stucco (SoCal tan) and horizontal lap siding (Midwest white). Tiled u by the bay, v by the floor, so a wall of
    n floors shows n rows of windows"""
    n = WALL_N
    ppm = n / HOUSE_BAY_M
    rng = random.Random(1950)
    fine = _noise(rng, n, 180, 0.9)
    # stucco
    g = Image.blend(_noise(rng, n, 8, 26), fine, 0.5).point(lambda v: 196 + v * 44 // 255)
    img = Image.merge("RGB", (g, g.point(lambda v: v * 92 // 100), g.point(lambda v: v * 74 // 100)))
    d = ImageDraw.Draw(img)
    _window(d, n / 2, n - 0.9 * ppm, 1.2 * ppm, 1.4 * ppm)
    img.save(out_dir / "stucco_wall_diffuse.jpg", quality=88, optimize=True)
    _normal_from_height(fine.point(lambda v: v // 3), 1.2).save(out_dir / "stucco_wall_normal.jpg", quality=88, optimize=True)
    # lap siding: 6 in boards, a shadow line under each
    board = int(0.152 * ppm)
    prof = [218 - 70 * math.exp(-(((y % board) - 2) / 2.2) ** 2) for y in range(n)]
    col = Image.new("L", (1, n))
    col.putdata([int(v) for v in prof])
    col = col.resize((n, n))
    g2 = ImageChops.multiply(col, fine.point(lambda v: 236 + v * 19 // 255))
    img = Image.merge("RGB", (g2, g2, g2.point(lambda v: max(0, v - 6))))
    d = ImageDraw.Draw(img)
    _window(d, n / 2, n - 0.9 * ppm, 1.2 * ppm, 1.4 * ppm)
    img.save(out_dir / "siding_wall_diffuse.jpg", quality=88, optimize=True)
    _normal_from_height(col, 2.5).save(out_dir / "siding_wall_normal.jpg", quality=88, optimize=True)


def shingle_roof(out_dir: Path) -> None:
    """asphalt shingle courses, one tile = SHINGLE_TILE_M: 5 in exposure, staggered tabs, grey-brown granules"""
    n = 512
    ppm = n / SHINGLE_TILE_M
    rng = random.Random(1977)
    base = Image.new("RGB", (n, n), (96, 88, 80))
    d = ImageDraw.Draw(base)
    course = int(0.127 * ppm)
    tab = int(0.3 * ppm)
    y = 0
    row = 0
    while y < n:
        off = (tab // 2) if row % 2 else 0
        x = -off
        while x < n:
            c = rng.randrange(-14, 14)
            d.rectangle((x, y, x + tab - 2, y + course - 2), fill=(96 + c, 88 + c, 80 + c))
            x += tab
        d.line((0, y + course - 1, n, y + course - 1), fill=(48, 44, 40))
        y += course
        row += 1
    f = _noise(rng, n, 200, 0.7).point(lambda v: 210 + v * 45 // 255)
    ImageChops.multiply(base, Image.merge("RGB", (f, f, f))).save(out_dir / "shingle_roof_diffuse.jpg", quality=88, optimize=True)


# --- the third batch (ledger 0094, Kevin 2026-11-18: "the buildings are all flat on milford and high plains") ---------------
# numpy, imported here only: the first two batches stay Pillow only and their bytes are untouched. Every layout and size
# below is [invented] (no photograph of either site's walls is in the repo) unless it says otherwise; the colours of the
# white and tan containers are the roofs of Milford's pad sheds S1 / S2 as NAIP 2022 shows them (the median pixel inside
# each footprint, tools/plan_buildings.py roof_colour) [measured], the walls assumed to wear the roof's paint [invented].
FACADE_SEED = 20261118
CONTAINER_RGB = {"white": (199, 214, 205), "tan": (218, 185, 153), "blue": (52, 90, 140)}
METAL_RGB = (214, 215, 211)       # [invented] light grey siding (walls cannot be seen from above)
TILT_RGB = (184, 180, 171)        # [invented] weathered tilt-up concrete
RIB_H_M, RIB_FACE_DEG, RIB_TOP_M = 0.032, 52.0, 0.025    # R-panel: a 1.25 in rib (cited from memory) whose faces stand at 52 deg
                                                        # [invented, inside the 45-60 deg the audit asked for]
CORR_H_M, CORR_FACE_DEG = 0.036, 55.0                    # [invented by eye] a container side's corrugation, 11 per 3.05 m
ROOF_N_FINE = 2048                # the ribbed roof's normal: a 52 deg rib face is 4 px wide at 12 m a tile
MEMBRANE_SHEET_M = 3.0            # [invented] a single-ply membrane's sheet (10 ft rolls are common; cited from memory)


def _np():
    import numpy as np
    return np


def _grid(w_px, h_px, w_m, h_m):
    """metric coordinates of each pixel centre: X across (m from the left), Y up (m from the bottom), row 0 at the top"""
    np = _np()
    x = (np.arange(w_px) + 0.5) / w_px * w_m
    y = h_m - (np.arange(h_px) + 0.5) / h_px * h_m
    return np.meshgrid(x, y)


def _periodic(X, Y, pw, ph, seed, terms=48, fmax=6, power=1.6):
    """a smooth field periodic over pw x ph metres (so any cell of the same family meets its neighbours), about -1..1"""
    np = _np()
    rng = np.random.default_rng(seed)
    f = np.zeros_like(X)
    for _ in range(terms):
        kx, ky = int(rng.integers(-fmax, fmax + 1)), int(rng.integers(0, fmax + 1))
        if kx == 0 and ky == 0:
            continue
        a = 1.0 / (kx * kx + ky * ky) ** (power / 2)
        f += a * np.cos(2 * np.pi * (kx * X / pw + ky * Y / ph) + rng.uniform(0, 2 * np.pi))
    return f / (np.abs(f).max() or 1.0)


def _trapezoid(x, period, depth, face_deg, top_w, centre):
    """a trapezoidal rib (or corrugation) profile, its height at x (m): a flat top ``top_w`` wide, faces at ``face_deg``"""
    np = _np()
    run = depth / math.tan(math.radians(face_deg))
    d = np.abs(((x - centre + period / 2) % period) - period / 2)        # distance to the nearest rib centre
    return np.clip((top_w / 2 + run - d) / run, 0.0, 1.0) * depth


def _box(X, Y, x0, y0, x1, y1):
    return (X >= x0) & (X < x1) & (Y >= y0) & (Y < y1)


def _paint(alb, mask, rgb, k=1.0):
    np = _np()
    alb[mask] = alb[mask] * (1 - k) + np.array(rgb, dtype=float) * k


def _normal_np(H, w_m, h_m):
    """height (m, row 0 at the top) -> the OpenGL normal map _normal_from_height writes (+y up the image)"""
    np = _np()
    hp, wp = H.shape
    grow, gcol = np.gradient(H)
    gx = gcol / (w_m / wp)
    gy = -grow / (h_m / hp)
    ln = np.sqrt(gx * gx + gy * gy + 1.0)
    n = np.stack([-gx / ln, -gy / ln, 1.0 / ln], axis=-1)
    return np.clip(np.round(127.5 + 127.5 * n), 0, 255).astype(np.uint8)


def _metal_base(X, Y, w_m, h_m, seed):
    """R-panel siding: major ribs every 0.3048 m (12 per bay, a pan at each bay edge), two low stiffeners in each pan, a
    faint periodic weathering; the ribs' feet a little darker (they shade)"""
    np = _np()
    H = _trapezoid(X, 0.3048, RIB_H_M, RIB_FACE_DEG, RIB_TOP_M, 0.1524)
    for c in (0.1524 + 0.3048 / 3, 0.1524 + 2 * 0.3048 / 3):
        d = np.abs(((X - c + 0.1524) % 0.3048) - 0.1524)
        H += np.where(d < 0.015, 0.003 * np.cos(d / 0.015 * np.pi / 2) ** 2, 0.0)
    w = _periodic(X, Y, w_m, h_m, seed, fmax=5)
    alb = np.ones(X.shape + (3,)) * np.array(METAL_RGB, dtype=float)
    alb *= (1.0 + 0.025 * w)[..., None]
    foot = (H > 0.002) & (H < 0.012)
    alb[foot] *= 0.93
    return alb, H


def _tilt_base(X, Y, w_m, h_m, seed, rng):
    """tilt-up concrete: periodic cure blotches, fine grain, a caulked joint at both bay edges, a reveal at 4.6 m"""
    np = _np()
    blot = _periodic(X, Y, w_m, 8.0, seed, fmax=4, power=1.8)
    alb = np.ones(X.shape + (3,)) * np.array(TILT_RGB, dtype=float)
    alb *= (1.0 + 0.05 * blot + 0.025 * rng.standard_normal(X.shape))[..., None]
    H = 0.001 * rng.standard_normal(X.shape) + 0.002 * blot
    joint = (X < 0.035) | (X > w_m - 0.035)
    _paint(alb, joint, (78, 76, 72))
    H[joint] -= 0.012
    rev = (np.abs((Y % 8.0) - 4.6) < 0.0125)
    _paint(alb, rev, (150, 146, 138), 0.8)
    H[rev] -= 0.012
    return alb, H


def _container_base(X, Y, w_m, h_m, rgb, seed, rng, period):
    """a container's corrugated steel: trapezoidal corrugation, the top and bottom rails, dents, a few rust runs"""
    np = _np()
    H = _trapezoid(X, period, CORR_H_M, CORR_FACE_DEG, period * 0.36, period / 2)
    H += 0.003 * _periodic(X, Y, w_m, h_m, seed, fmax=4)
    alb = np.ones(X.shape + (3,)) * np.array(rgb, dtype=float)
    alb *= (1.0 + 0.03 * _periodic(X, Y, w_m, h_m, seed + 1, fmax=6) + 0.015 * rng.standard_normal(X.shape))[..., None]
    alb[(H < 0.004)] *= 0.94                                      # the corrugation's inner flats sit in shade
    top = Y > h_m - 0.12
    bot = Y < 0.16
    H[top] = 0.04
    H[bot] = 0.045
    alb[top] = np.array(rgb, dtype=float) * 0.9
    alb[bot] = np.array(rgb, dtype=float) * 0.72
    for _ in range(4):                                            # rust runs down from the top rail
        x0 = rng.uniform(0.1, w_m - 0.1)
        ln = rng.uniform(0.3, 1.4)
        m = (np.abs(X - x0) < rng.uniform(0.01, 0.03)) & (Y > h_m - 0.12 - ln) & (Y < h_m - 0.1)
        _paint(alb, m, (122, 74, 44), 0.35)
    _paint(alb, bot & (rng.random(X.shape) < 0.25), (110, 70, 44), 0.5)
    return alb, H


def _louvre(alb, H, X, Y, x0, y0, x1, y1, pitch=0.1, rgb=(92, 94, 96)):
    """a louvre: a frame and blades sloped 45 deg, dark gaps between them"""
    np = _np()
    m = _box(X, Y, x0, y0, x1, y1)
    frame = m & ~_box(X, Y, x0 + 0.05, y0 + 0.05, x1 - 0.05, y1 - 0.05)
    t = ((Y - y0) % pitch) / pitch
    _paint(alb, m, rgb)
    alb[m & (t < 0.25) & ~frame] *= 0.35
    H[m] = np.where(frame[m], 0.03, 0.03 * t[m] * 0.9)
    return m


def _fwindow(alb, H, X, Y, x0, y0, x1, y1, mullions=1, frame_rgb=(232, 232, 228)):
    np = _np()
    m = _box(X, Y, x0, y0, x1, y1)
    _paint(alb, m, frame_rgb)
    H[m] = 0.012
    g = _box(X, Y, x0 + 0.05, y0 + 0.05, x1 - 0.05, y1 - 0.05)
    _paint(alb, g, (38, 46, 56))
    sky = g & (Y > y0 + (y1 - y0) * 0.62)
    _paint(alb, sky, (98, 118, 140))
    H[g] = -0.03
    for k in range(1, mullions + 1):
        xm = x0 + (x1 - x0) * k / (mullions + 1)
        mm = g & (np.abs(X - xm) < 0.025)
        _paint(alb, mm, frame_rgb)
        H[mm] = 0.0
    _paint(alb, _box(X, Y, x0 - 0.04, y0 - 0.05, x1 + 0.04, y0), (200, 200, 196))     # the sill
    return m


def _door(alb, H, X, Y, x0, x1, top, rgb, frame_rgb):
    fr = _box(X, Y, x0 - 0.05, 0.0, x1 + 0.05, top + 0.05)
    _paint(alb, fr, frame_rgb)
    H[fr] = 0.015
    d = _box(X, Y, x0, 0.0, x1, top)
    _paint(alb, d, rgb)
    H[d] = -0.01
    hx = x1 - 0.12 if x1 - x0 < 1.2 else (x0 + x1) / 2
    hd = _box(X, Y, hx - 0.06, 0.92, hx + 0.02, 1.0)
    _paint(alb, hd, (40, 40, 42))
    H[hd] = 0.02
    return d


def _cell(name, w_px, h_px, rng):
    """one facade cell: (albedo HxWx3 float, height HxW metres, w_m, h_m)"""
    import circuit_facades as cf
    np = _np()
    _, _, _, w_m, h_m, _ = cf.CELLS[name]
    X, Y = _grid(w_px, h_px, w_m, h_m)
    if name.startswith(("metal_", "grime_metal")):
        alb, H = _metal_base(X, Y, w_m, cf.METAL_MODULE_M, FACADE_SEED)
        base = _box(X, Y, 0.0, 0.0, w_m, 0.06)                      # the base angle
        _paint(alb, base, (176, 178, 178))
        H[base] = 0.02
        if name == "metal_rollup":
            x0, x1, top = (w_m - 2.74) / 2, (w_m + 2.74) / 2, 2.44
            jam = _box(X, Y, x0 - 0.07, 0.0, x1 + 0.07, top) & ~_box(X, Y, x0, 0.0, x1, top)
            _paint(alb, jam, (236, 236, 232))
            H[jam] = 0.03
            d = _box(X, Y, x0, 0.0, x1, top)
            t = (Y % 0.0762) / 0.0762
            slat = np.array((170, 172, 175), dtype=float) * (0.94 + 0.06 * np.sin(np.pi * t))[..., None]
            alb[d] = slat[d]
            H[d] = 0.006 * np.sin(np.pi * t[d]) ** 2
            seal = _box(X, Y, x0, 0.0, x1, 0.035)
            _paint(alb, seal, (28, 28, 30))
            bar = _box(X, Y, x0, 0.035, x1, 0.11)
            _paint(alb, bar, (150, 152, 155))
            H[bar] = 0.012
            for hx in (x0 + 0.35, x1 - 0.45):
                hd = _box(X, Y, hx, 0.14, hx + 0.1, 0.2)
                _paint(alb, hd, (50, 50, 52))
            hood = _box(X, Y, x0 - 0.12, top, x1 + 0.12, top + 0.34)
            _paint(alb, hood, (196, 197, 195))
            H[hood] = 0.25
            _paint(alb, _box(X, Y, x0 - 0.12, top + 0.32, x1 + 0.12, top + 0.34), (236, 236, 232))
        elif name == "metal_mandoor":
            _door(alb, H, X, Y, 0.55, 1.464, 2.13, (88, 92, 96), (236, 236, 232))
            _fwindow(alb, H, X, Y, 2.0, 1.1, 3.2, 2.0)
            lamp = _box(X, Y, 0.93, 2.36, 1.09, 2.48)
            _paint(alb, lamp, (60, 60, 62))
            H[lamp] = 0.12
        elif name == "metal_window":
            _fwindow(alb, H, X, Y, (w_m - 2.44) / 2, 1.0, (w_m + 2.44) / 2, 2.0, mullions=2)
        elif name == "grime_metal":
            a = (0.42 * np.exp(-Y / 0.22) + 0.12 * np.exp(-Y / 0.6))
            a *= 0.75 + 0.5 * rng.random(X.shape)
            alb[:] = alb * (1 - a[..., None]) + np.array((96, 84, 70), dtype=float) * a[..., None]
            for _ in range(10):
                xd = rng.uniform(0.0, w_m)
                m = (np.abs(X - xd) < 0.012) & (Y < rng.uniform(0.2, 0.7))
                _paint(alb, m, (120, 92, 66), 0.4)
    elif name.startswith(("tilt_", "grime_tilt")):
        alb, H = _tilt_base(X, Y, w_m, h_m, FACADE_SEED + 1, rng)
        if name == "tilt_dock":
            x0, x1, sill, top = 2.63, 5.37, 1.22, 4.27
            face = _box(X, Y, x0 - 0.5, 0.0, x1 + 0.5, sill)
            alb[face] *= 0.9
            for bx in (x0 - 0.3, x1 + 0.05):
                b = _box(X, Y, bx, 0.72, bx + 0.25, 1.16)
                _paint(alb, b, (30, 30, 30))
                H[b] = 0.1
            lip = _box(X, Y, x0, sill - 0.05, x1, sill)
            _paint(alb, lip, (130, 130, 128))
            seal = _box(X, Y, x0 - 0.3, sill - 0.05, x1 + 0.3, top + 0.4) & ~_box(X, Y, x0, sill, x1, top)
            _paint(alb, seal, (34, 34, 35))
            H[seal] = 0.3
            d = _box(X, Y, x0, sill, x1, top)
            sec = ((Y - sill) % 0.7625) / 0.7625
            _paint(alb, d, (214, 214, 208))
            H[d] = 0.004 * np.sin(2 * np.pi * sec[d] * 2) ** 2
            j = d & (sec < 0.02)
            alb[j] *= 0.6
            H[j] = -0.005
            vis = d & _box(X, Y, x0 + 0.4, sill + 1.6, x1 - 0.4, sill + 1.9)
            _paint(alb, vis, (60, 70, 80))
            lamp = _box(X, Y, x1 + 0.55, top + 0.1, x1 + 0.75, top + 0.25)
            _paint(alb, lamp, (60, 60, 62))
            H[lamp] = 0.15
        elif name == "tilt_mandoor":
            _door(alb, H, X, Y, 3.543, 4.457, 2.13, (78, 70, 60), (120, 116, 110))
            can = _box(X, Y, 3.2, 2.45, 4.8, 2.6)
            _paint(alb, can, (150, 152, 154))
            H[can] = 0.4
            sh = _box(X, Y, 3.2, 2.2, 4.8, 2.45) & ~_box(X, Y, 3.493, 0.0, 4.507, 2.18)
            alb[sh] *= 0.82
            lamp = _box(X, Y, 3.92, 2.85, 4.08, 3.0)
            _paint(alb, lamp, (60, 60, 62))
            H[lamp] = 0.12
            _louvre(alb, H, X, Y, 3.25, 5.2, 4.75, 6.2)
        elif name == "tilt_louvre":
            _louvre(alb, H, X, Y, 2.8, 5.0, 5.2, 6.6)
            pipe = np.abs(X - 7.62) < 0.075
            _paint(alb, pipe, (142, 144, 142))
            H[pipe] = 0.05 * np.sqrt(np.clip(1 - ((X[pipe] - 7.62) / 0.075) ** 2, 0, 1))
            boot = pipe & (Y < 0.3)
            alb[boot] *= 0.6
            for ys in (2.0, 4.0, 6.0):
                st = pipe & (np.abs(Y - ys) < 0.02)
                alb[st] *= 0.7
        elif name == "grime_tilt":
            a = 0.38 * np.exp(-Y / 0.3) * (0.7 + 0.6 * rng.random(X.shape))
            alb[:] = alb * (1 - a[..., None]) + np.array((104, 98, 90), dtype=float) * a[..., None]
            eff = (rng.random(X.shape) < 0.01) & (Y < 0.5)
            _paint(alb, eff, (214, 212, 204), 0.5)
    elif name.startswith("container_"):
        colour = name.rsplit("_", 1)[1]
        rgb = CONTAINER_RGB[colour]
        if name.startswith("container_side"):
            alb, H = _container_base(X, Y, w_m, h_m, rgb, FACADE_SEED + 2, rng, w_m / 11)
        else:
            alb, H = _container_base(X, Y, w_m, h_m, rgb, FACADE_SEED + 3, rng, w_m / 10)
            H *= 0.6
            seam = np.abs(X - w_m / 2) < 0.012
            _paint(alb, seam, (30, 30, 30))
            H[seam] = -0.01
            for xe in (0.0, w_m):
                fr = np.abs(X - xe) < 0.07
                _paint(alb, fr, np.array(rgb) * 0.85)
                H[fr] = 0.05
            for xb in (0.26, 0.95, w_m - 0.95, w_m - 0.26):
                bar = (np.abs(X - xb) < 0.0135) & (Y > 0.16) & (Y < h_m - 0.12)
                _paint(alb, bar, np.array(rgb) * 0.7)
                H[bar] = 0.05 + 0.0135 * np.sqrt(np.clip(1 - ((X[bar] - xb) / 0.0135) ** 2, 0, 1))
                for yk in (0.22, h_m - 0.2):
                    k_ = _box(X, Y, xb - 0.04, yk - 0.04, xb + 0.04, yk + 0.04)
                    _paint(alb, k_, (60, 60, 60))
                    H[k_] = 0.07
                hd = _box(X, Y, xb - 0.02, 1.0, xb + 0.2, 1.06)
                _paint(alb, hd, (50, 50, 50))
                H[hd] = 0.09
            for xe in (0.03, w_m - 0.03):
                for yh in (0.45, 1.05, 1.65, 2.2):
                    hg = _box(X, Y, xe - 0.035, yh, xe + 0.035, yh + 0.1)
                    _paint(alb, hg, (70, 70, 70))
                    H[hg] = 0.08
    elif name == "rtu_side":
        alb = np.ones(X.shape + (3,)) * np.array((168, 170, 170), dtype=float)
        alb *= (1.0 + 0.03 * _periodic(X, Y, w_m, h_m, FACADE_SEED + 4, fmax=5))[..., None]
        H = np.zeros_like(X)
        _louvre(alb, H, X, Y, 0.1, 0.15, 1.3, 1.35, pitch=0.05, rgb=(150, 152, 152))
        pnl = _box(X, Y, 1.4, 0.15, 1.9, 1.35)
        _paint(alb, pnl, (176, 178, 178))
        H[pnl] = 0.006
        for sx in (1.45, 1.85):
            for sy in (0.2, 1.3):
                sc = _box(X, Y, sx - 0.008, sy - 0.008, sx + 0.008, sy + 0.008)
                _paint(alb, sc, (90, 90, 90))
        hd = _box(X, Y, 1.62, 0.7, 1.68, 0.85)
        _paint(alb, hd, (60, 60, 62))
        H[hd] = 0.02
        _paint(alb, _box(X, Y, 0.0, h_m - 0.08, w_m, h_m), (204, 206, 206))
        _paint(alb, _box(X, Y, 0.0, 0.0, w_m, 0.08), (120, 122, 122))
        H[np.abs(X - 0.0) < 0.01] = -0.005
    else:
        raise ValueError(name)
    return alb, H, w_m, h_m


def circuit_facades(out_dir: Path) -> None:
    """the facade atlas (tools/circuit_facades.py: its cell table): every cell painted at its slot's drawn size, the gutter
    filled with the cell's own edge pixels, the diffuse and its normal map (4:4:4, so a 4 px rib face keeps its tilt)"""
    np = _np()
    sys.path.insert(0, str(AIROSO / "tools"))
    import circuit_facades as cf
    n = cf.ATLAS_PX
    dif = np.zeros((n, n, 3), dtype=np.uint8)
    nor = np.zeros((n, n, 3), dtype=np.uint8)
    rng = np.random.default_rng(FACADE_SEED)
    for name in cf.CELLS:
        x0, y0, x1, y1 = cf.cell_px(name)
        alb, H, w_m, h_m = _cell(name, x1 - x0, y1 - y0, rng)
        a = np.clip(np.round(alb), 0, 255).astype(np.uint8)
        nm = _normal_np(H, w_m, h_m)
        p = cf.PAD_PX
        dif[y0 - p:y1 + p, x0 - p:x1 + p] = np.pad(a, ((p, p), (p, p), (0, 0)), mode="edge")
        nor[y0 - p:y1 + p, x0 - p:x1 + p] = np.pad(nm, ((p, p), (p, p), (0, 0)), mode="edge")
    Image.fromarray(dif, "RGB").save(out_dir / cf.ATLAS_DIFFUSE, quality=90, optimize=True)
    Image.fromarray(nor, "RGB").save(out_dir / cf.ATLAS_NORMAL, quality=92, subsampling=0, optimize=True)


def roof_normals(out_dir: Path) -> None:
    """two roof normals at the author's ROOF_TILE_DEFAULT_M (12 m a tile), each bound by a track's texture_overrides on its
    ROOFTOP_<class> rows next to the class's own unchanged diffuse:
      roof_membrane_normal.jpg  a single-ply membrane: a welded lap every MEMBRANE_SHEET_M (u), an end lap at the tile's edge
                                (v), fastener plates under each lap every 0.3 m, a faint billow between [all invented]
      roof_rib_normal.jpg       ribbed metal: the walls' R-panel rib on 0.3 m centres (40 a tile), running up a pitched
                                roof's slope (v), its faces at RIB_FACE_DEG"""
    np = _np()
    tile = 12.0
    n = 1024
    X, Y = _grid(n, n, tile, tile)
    rng = np.random.default_rng(FACADE_SEED + 7)
    H = 0.008 * _periodic(X, Y, tile, tile, FACADE_SEED + 8, fmax=10, power=1.2)
    for s in np.arange(0.0, tile, MEMBRANE_SHEET_M):
        d = (X - s) % tile
        H += np.where(d < 0.10, 0.003, 0.0)                            # the lap: the next sheet laid over this one
        H += np.where(np.abs(d - 0.05) < 0.012, 0.002, 0.0)             # its weld bead
        for yp in np.arange(0.15, tile, 0.3):
            r = np.hypot(d - 0.05, Y - yp)
            H += np.where(r < 0.04, 0.002 * (1 - r / 0.04), 0.0)
    H += np.where((Y % tile) < 0.10, 0.003, 0.0)
    H += 0.0002 * rng.standard_normal(X.shape)
    Image.fromarray(_normal_np(H, tile, tile), "RGB").save(out_dir / "roof_membrane_normal.jpg", quality=90, subsampling=0, optimize=True)
    n = ROOF_N_FINE
    X, Y = _grid(n, n, tile, tile)
    H = _trapezoid(X, 0.3, RIB_H_M, RIB_FACE_DEG, RIB_TOP_M, 0.15)
    for c in (0.05, 0.25):
        d = np.abs(((X - c + 0.15) % 0.3) - 0.15)
        H += np.where(d < 0.015, 0.003 * np.cos(d / 0.015 * np.pi / 2) ** 2, 0.0)
    H += 0.0015 * _periodic(X, Y, tile, tile, FACADE_SEED + 9, fmax=8)
    Image.fromarray(_normal_np(H, tile, tile), "RGB").save(out_dir / "roof_rib_normal.jpg", quality=90, subsampling=0, optimize=True)


def tent_fabric(out_dir: Path) -> None:
    """a clearspan tent's wall and roof panel, one tile = FABRIC_BAY_M x FABRIC_BAY_M as fabric(): the keder bead of the
    frame at u = 0 (every 5 m: the legs on a wall, the rafters on the roof), the panel bowing between them and its tension
    creases fanning from the frame. No skirt: the tile repeats up the roof's slope, so a foot band would stripe the roof. The
    same off-white as fabric() [invented]; bound by a track's texture_overrides["BUILDING_FABRIC"] only (Nevada Nights keeps
    fabric_white_*)"""
    np = _np()
    n = FABRIC_N
    w = FABRIC_BAY_M
    X, Y = _grid(n, n, w, w)
    rng = np.random.default_rng(FACADE_SEED + 5)
    d = np.minimum(X, w - X)                                               # distance to the frame
    H = 0.012 * np.clip(1 - d / 0.03, 0, 1)                                # the keder bead
    sag = 0.02 * np.sin(np.pi * X / w)                                     # the panel bows between two legs
    crease = 0.003 * np.cos(2 * np.pi * (X + 0.6 * Y) / 0.35) * np.exp(-d / 0.7)
    crease += 0.003 * np.cos(2 * np.pi * (X - 0.6 * Y) / 0.35) * np.exp(-d / 0.7)
    H = H - sag + crease + 0.004 * _periodic(X, Y, w, w, FACADE_SEED + 6, fmax=6)
    g = 226 + 14 * _periodic(X, Y, w, w, FACADE_SEED + 10, fmax=5) + 3 * rng.standard_normal(X.shape)
    alb = np.stack([g, g, g - 6], axis=-1)
    alb[d < 0.03] *= 0.86
    Image.fromarray(np.clip(np.round(alb), 0, 255).astype(np.uint8), "RGB").save(out_dir / "fabric_tent_diffuse.jpg", quality=90, optimize=True)
    Image.fromarray(_normal_np(H, w, w), "RGB").save(out_dir / "fabric_tent_normal.jpg", quality=90, subsampling=0, optimize=True)


def circuit_batch(tex_dir: Path) -> None:
    circuit_facades(tex_dir)
    roof_normals(tex_dir)
    tent_fabric(tex_dir)


CIRCUIT_FILES = ("circuit_facade_diffuse.jpg", "circuit_facade_normal.jpg", "roof_membrane_normal.jpg", "roof_rib_normal.jpg",
                 "fabric_tent_diffuse.jpg", "fabric_tent_normal.jpg")


def write_all(tex_dir: Path, model_dir: Path) -> None:
    fabric(tex_dir)
    cone_texture(tex_dir)
    scrub_atlas(tex_dir)
    cone_model(model_dir)
    tiltup(tex_dir)
    metal(tex_dir)
    roofs(tex_dir)
    pad(tex_dir)
    wbeam(tex_dir)
    ghost(tex_dir)
    deciduous_atlas(tex_dir)
    prairie_atlas(tex_dir)
    tecpro(tex_dir)
    krail(tex_dir)
    tyre_wall(tex_dir)
    drystone(tex_dir)
    conifer_atlas(tex_dir)
    house_walls(tex_dir)
    shingle_roof(tex_dir)
    circuit_batch(tex_dir)


TEX_FILES = ("fabric_white_diffuse.jpg", "fabric_white_normal.jpg", "traffic_cone_diffuse.png", "desert_scrub_atlas.png",
             "tiltup_wall_diffuse.jpg", "tiltup_wall_normal.jpg", "metal_wall_diffuse.jpg", "metal_wall_normal.jpg",
             "roof_white_diffuse.jpg", "roof_tan_diffuse.jpg", "roof_dark_diffuse.jpg", "pad_asphalt_diffuse.jpg",
             "wbeam_rail_diffuse.png", "ghost_alpha.png", "deciduous_atlas.png", "prairie_atlas.png",
             "tecpro_diffuse.png", "krail_bluewhite_diffuse.png", "tyre_wall_diffuse.png", "drystone_diffuse.jpg", "drystone_normal.jpg", "conifer_foothill_atlas.png",
             "stucco_wall_diffuse.jpg", "stucco_wall_normal.jpg", "siding_wall_diffuse.jpg", "siding_wall_normal.jpg", "shingle_roof_diffuse.jpg") + CIRCUIT_FILES
MODEL_FILES = ("traffic_cone.obj", "traffic_cone.json")


CHECK_MEAN_DIFF = 0.25   # [invented] of 255, per channel. Pillow's encoders and resampling differ by a few pixels between
                         # platforms (the Windows box, this Mac and the Linux CI runner), so the bytes can't be the test


def _same_image(a: Path, b: Path) -> bool:
    x, y = Image.open(a).convert("RGBA"), Image.open(b).convert("RGBA")
    if x.size != y.size:
        return False
    return max(ImageStat.Stat(ImageChops.difference(x, y)).mean) <= CHECK_MEAN_DIFF


def main() -> int:
    if "--only" in sys.argv:
        # one batch alone (ledger 0094: "circuit"), so the files of the other batches are never re-encoded by this machine's
        # Pillow (their bytes stay the committed ones)
        batch = sys.argv[sys.argv.index("--only") + 1]
        if batch != "circuit":
            print(f"--only knows one batch, circuit (got {batch!r})")
            return 2
        circuit_batch(TEX)
        print("wrote", ", ".join(CIRCUIT_FILES))
        return 0
    if "--check" not in sys.argv:
        write_all(TEX, MODELS)
        print("wrote", ", ".join(TEX_FILES + MODEL_FILES))
        return 0
    with tempfile.TemporaryDirectory() as d:
        t = Path(d)
        write_all(t, t)
        bad = [f for f in TEX_FILES if not _same_image(t / f, TEX / f)]
        bad += [f for f in MODEL_FILES if hashlib.md5((t / f).read_bytes()).digest() != hashlib.md5((MODELS / f).read_bytes()).digest()]
    if bad:
        print("differ from the generator:", bad)
        return 1
    print("bespoke assets match the generator")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

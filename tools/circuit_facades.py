"""Circuit facades (ledger 0094, Kevin 2026-11-18: "the buildings are all flat on milford and high plains"): the facade
atlas's cell table and the pure wall, roof and rooftop-unit builders tools/author_bespoke_blend.py stands the opt-in skins
with. No bpy, no Pillow: tools/make_bespoke_assets.py paints the cells this table names, the author tool maps faces into them,
and tests import it directly.

THE ATLAS. One diffuse + one normal map (ATLAS_DIFFUSE / ATLAS_NORMAL, ATLAS_PX square) of 4 x 4 slots of SLOT_PX, each
cell drawn inside its slot PAD_PX clear of the slot's edge and the gutter filled by repeating the cell's own edge pixels, so
a filtered sample (mip 4 still holds 1.5 px of gutter) never reaches a neighbour. A cell is ONE facade module: one bay wide
(w_m) by one module tall (h_m). The engine-july pbr table is frozen (tracks/san-diego-lake-murray/engine-july-snapshot), so
the atlas binds through the rows that already exist: a track opts in with texture_overrides on BUILDING_METAL /
FARBLOCK_METAL / BUILDING_TILTUP / FARBLOCK_TILTUP naming the atlas, and every block on such a row must wear an atlas skin
(the author refuses a mix, which would show the old tile's UVs on the atlas).

THE WALL. Each footprint edge is cut into whole bays (bays(): n = round(L / w_m), at least one), so an opening is never cut
at a corner; each bay is one cell wide. The levels run bottom -> door level -> (grime band) -> one module -> plain modules ->
the top, so the openings stand at the door level and the wall above them is the skin's plain cell. Every face shares its
corner vertices with its neighbours: a building's walls stay ONE island (engine-july's prep re-seats a building by island,
its base ring = the vertices at its lowest z, in index order), with the base ring allocated first in ring order.

Every layout below (which bay takes a door, a window or a louvre; the door and window sizes in make_bespoke_assets.py) is
[invented]: no photograph of either site's walls exists in the repo. They are kept plausible for an industrial proving ground
(Milford) and a club paddock (High Plains).
"""
from __future__ import annotations

import math

ATLAS_PX = 2048
SLOT_PX = 512
PAD_PX = 24                     # [invented] gutter: 24 px = 1.5 px at mip 4
ATLAS_DIFFUSE = "circuit_facade_diffuse.jpg"
ATLAS_NORMAL = "circuit_facade_normal.jpg"
EPS_Z = 0.06                    # levels closer than this merge: the prep's base ring is every vertex within 0.05 m of the lowest

# R-panel siding: major ribs on 0.3048 m (12 in) centres, a 36 in cover (cited from memory, not re-read); a bay of 12 ribs
METAL_BAY_M = 12 * 0.3048
METAL_MODULE_M = 3.0            # [invented] a one-storey garage / post module; a lower wall shows its lower part
TILT_BAY_M = 8.0                # tools/make_bespoke_assets.py PANEL_BAY_M [invented]: one tilt-up panel
TILT_MODULE_M = 8.0             # [invented] the door storey of a plant; a taller wall carries plain panels above
CONTAINER_SIDE_M = 3.05         # [invented] a quarter of a 40 ft box's side (12.19 m, ISO 668, cited from memory)
CONTAINER_END_M = 2.438         # ISO 668 width, 8 ft (cited from memory)
CONTAINER_H_M = 2.6             # ISO 668 standard height 8 ft 6 in = 2.591 m (cited from memory)
GRIME_H_M = 1.0                 # the grime cells' module (the band is squeezed onto the whole cell, whatever its height)
RTU_BAY_M = 2.0                 # [invented] one rooftop-unit side panel
RTU_H_M = 1.5                   # [invented] the panel's module

# name -> (slot column, slot row, half, w_m, h_m, ground). half: None = the whole slot, 0 = its upper half, 1 = its lower
# half. ground: True when the cell's opening reaches the door level (a grime band never paints over it)
CELLS = {
    "metal_plain":         (0, 0, None, METAL_BAY_M, METAL_MODULE_M, False),
    "metal_rollup":        (1, 0, None, METAL_BAY_M, METAL_MODULE_M, True),
    "metal_mandoor":       (2, 0, None, METAL_BAY_M, METAL_MODULE_M, True),
    "metal_window":        (3, 0, None, METAL_BAY_M, METAL_MODULE_M, False),
    "tilt_plain":          (0, 1, None, TILT_BAY_M, TILT_MODULE_M, False),
    "tilt_dock":           (1, 1, None, TILT_BAY_M, TILT_MODULE_M, False),   # a dock door's sill stands 1.22 m up
    "tilt_mandoor":        (2, 1, None, TILT_BAY_M, TILT_MODULE_M, True),
    "tilt_louvre":         (3, 1, None, TILT_BAY_M, TILT_MODULE_M, False),
    "container_side_white": (0, 2, None, CONTAINER_SIDE_M, CONTAINER_H_M, False),
    "container_side_tan":  (1, 2, None, CONTAINER_SIDE_M, CONTAINER_H_M, False),
    "container_side_blue": (2, 2, None, CONTAINER_SIDE_M, CONTAINER_H_M, False),
    "rtu_side":            (3, 2, None, RTU_BAY_M, RTU_H_M, False),
    "container_doors_white": (0, 3, None, CONTAINER_END_M, CONTAINER_H_M, True),
    "container_doors_tan": (1, 3, None, CONTAINER_END_M, CONTAINER_H_M, True),
    "container_doors_blue": (2, 3, None, CONTAINER_END_M, CONTAINER_H_M, True),
    "grime_metal":         (3, 3, 0, METAL_BAY_M, GRIME_H_M, False),
    "grime_tilt":          (3, 3, 1, TILT_BAY_M, GRIME_H_M, False),
}

# skin -> its family (the pbr row it rides: BUILDING_/FARBLOCK_<family>), module, plain and grime cells, layout rule
SKINS = {
    "garage": {"family": "METAL", "module_m": METAL_MODULE_M, "plain": "metal_plain", "grime": "grime_metal", "rule": "garage"},
    "post": {"family": "METAL", "module_m": METAL_MODULE_M, "plain": "metal_plain", "grime": "grime_metal", "rule": "post"},
    "shed": {"family": "METAL", "module_m": METAL_MODULE_M, "plain": "metal_plain", "grime": "grime_metal", "rule": "shed"},
    "plant": {"family": "TILTUP", "module_m": TILT_MODULE_M, "plain": "tilt_plain", "grime": "grime_tilt", "rule": "plant"},
}
for _c in ("white", "tan", "blue"):
    SKINS[f"container_{_c}"] = {"family": "METAL", "module_m": CONTAINER_H_M, "plain": f"container_side_{_c}", "grime": None,
                                "rule": "container", "colour": _c}
# a row of boxes side by side (High Plains' traced container stack, 24.9 x 12.2 m): one box per CONTAINER_END_M of the long
# side facing the lap (their doors), their front walls behind, the end boxes' corrugated sides on the short edges; each
# box's colour by ROW_COLOURS in turn [invented: NAIP 2023 shows coloured stripes, their colours not read]
SKINS["container_row"] = {"family": "METAL", "module_m": CONTAINER_H_M, "plain": "container_side_tan", "grime": None,
                          "rule": "container_row"}
ROW_COLOURS = ("blue", "tan", "white", "tan", "blue", "white", "white")
FAMILY_ROWS = {"METAL": ("BUILDING_METAL", "FARBLOCK_METAL"), "TILTUP": ("BUILDING_TILTUP", "FARBLOCK_TILTUP")}
RTU_PREFIX = "FARBLOCK_METAL_RTU"   # rooftop units: not BUILDING* (the prep would re-seat them onto the ground), the atlas row


def cell_px(name):
    """the cell's drawn rect in image pixels (x0, y0, x1, y1), y down"""
    col, row, half, _, _, _ = CELLS[name]
    x0, y0 = col * SLOT_PX, row * SLOT_PX
    if half is None:
        return x0 + PAD_PX, y0 + PAD_PX, x0 + SLOT_PX - PAD_PX, y0 + SLOT_PX - PAD_PX
    h = SLOT_PX // 2
    return x0 + PAD_PX, y0 + half * h + PAD_PX, x0 + SLOT_PX - PAD_PX, y0 + (half + 1) * h - PAD_PX


def cell_uv(name):
    """the cell's rect in Blender UV (u0, v0, u1, v1): v counts from the image's bottom"""
    x0, y0, x1, y1 = cell_px(name)
    return x0 / ATLAS_PX, 1.0 - y1 / ATLAS_PX, x1 / ATLAS_PX, 1.0 - y0 / ATLAS_PX


def atlas_uv(name, s, t):
    """a point of a cell, s across its bay and t up its module (both clamped to 0..1), in atlas UV"""
    u0, v0, u1, v1 = cell_uv(name)
    s = min(1.0, max(0.0, s))
    t = min(1.0, max(0.0, t))
    return (u0 + (u1 - u0) * s, v0 + (v1 - v0) * t)


def bays(length, bay_m):
    """whole bays along an edge: at least one, the nearest count to the length (so a bay stretches at most ~1.5x)"""
    return max(1, int(round(length / bay_m)))


def axes(ring):
    """the minimum-area box's long axis (unit) and its half sizes (long, short): the box tools/author_bespoke_blend.py
    oriented_box finds"""
    n = len(ring)
    best = None
    for i in range(n):
        a, b = ring[i], ring[(i + 1) % n]
        ex, ey = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(ex, ey)
        if ln < 1e-6:
            continue
        ux, uy = ex / ln, ey / ln
        vx, vy = -uy, ux
        us = [p[0] * ux + p[1] * uy for p in ring]
        vs = [p[0] * vx + p[1] * vy for p in ring]
        w, h = max(us) - min(us), max(vs) - min(vs)
        if best is None or w * h < best[0]:
            best = (w * h, (ux, uy), (vx, vy), w / 2, h / 2)
    _, u, v, hw, hh = best
    if hw < hh:
        u, hw, hh = v, hh, hw
    return u, hw, hh


def edge_kinds(ring, toward):
    """per ring edge (ring counter-clockwise from above): ("long" | "short" | "other", facing). facing = the outward normal
    dotted with ``toward`` (a unit vector from the footprint toward the lap): the edge that faces the track has the most"""
    u, _, _ = axes(ring)
    n = len(ring)
    out = []
    for i in range(n):
        a, b = ring[i], ring[(i + 1) % n]
        L = math.dist(a, b) or 1e-9
        dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        nx, ny = dy, -dx                                  # outward: the right of a -> b on a counter-clockwise ring
        along = abs(dx * u[0] + dy * u[1])
        kind = "long" if along > 0.9 else ("short" if along < 0.45 else "other")
        out.append((kind, nx * toward[0] + ny * toward[1]))
    return out


def _middle(n, cell, rest):
    return [cell if k == n // 2 else rest for k in range(n)]


def side_cells(skin, kinds, lengths):
    """the cell of every bay of every edge: [[cell, ...] per edge]. The layouts are [invented] (see the header)"""
    sk = SKINS[skin]
    rule, plain = sk["rule"], sk["plain"]
    n_e = len(kinds)
    longs = [i for i in range(n_e) if kinds[i][0] == "long"]
    shorts = [i for i in range(n_e) if kinds[i][0] == "short"]
    best = max(range(n_e), key=lambda i: kinds[i][1])
    worst = min(range(n_e), key=lambda i: kinds[i][1])
    front = max(longs, key=lambda i: kinds[i][1]) if longs else best
    door_end = max(shorts, key=lambda j: kinds[j][1]) if shorts else None
    out = []
    for i in range(n_e):
        if rule == "container":
            w = CONTAINER_END_M if kinds[i][0] == "short" else CONTAINER_SIDE_M
        elif rule == "container_row":
            w = CONTAINER_END_M if kinds[i][0] == "long" else CONTAINER_SIDE_M
        else:
            w = CELLS[plain][3]
        n = bays(lengths[i], w)
        kind = kinds[i][0]
        if rule == "garage":
            # a paddock garage row: a roll-up door in every bay of the side facing the lap, a man door in every fourth bay of
            # the back, one in the middle of each end
            if i == front:
                cells = ["metal_rollup"] * n
            elif kind == "long":
                cells = ["metal_mandoor" if k % 4 == 1 or (n < 2 and k == 0) else plain for k in range(n)]
            elif kind == "short":
                cells = _middle(n, "metal_mandoor", plain)
            else:
                cells = [plain] * n
        elif rule == "post":
            # a marshal post: windows on the side facing the lap and its two neighbours, the door on the far side
            cells = _middle(n, "metal_mandoor", plain) if i == worst else ["metal_window"] * n
        elif rule == "shed":
            cells = _middle(n, "metal_mandoor", plain) if i == best else [plain] * n
        elif rule == "container":
            # a box's long sides corrugated, its doors on the end facing the lap, the other end the corrugated front wall
            c = sk["colour"]
            cells = [f"container_doors_{c}"] * n if i == door_end else [f"container_side_{c}"] * n
        elif rule == "container_row":
            n_f = bays(lengths[front], CONTAINER_END_M)
            col = [ROW_COLOURS[j % len(ROW_COLOURS)] for j in range(n_f)]
            if i == front:
                cells = [f"container_doors_{col[k]}" for k in range(n)]
            elif kind == "long":                                  # the back runs the other way round the ring
                cells = [f"container_side_{col[max(0, min(n_f - 1, n_f - 1 - k))]}" for k in range(n)]
            elif kind == "short":
                end = col[-1] if i == (front + 1) % n_e else col[0]
                cells = [f"container_side_{end}"] * n
            else:
                cells = [plain] * n
        elif rule == "plant":
            # a plant's long walls: a dock door in every third panel (never a corner panel), a man door at each end of
            # them; its short walls: a man door in the middle, louvres high in every other panel
            if kind == "long" and n >= 3:
                cells = []
                for k in range(n):
                    if k in (0, n - 1):
                        cells.append("tilt_mandoor")
                    elif k % 3 == 1:
                        cells.append("tilt_dock")
                    else:
                        cells.append(plain)
            elif kind in ("long", "short"):
                cells = ["tilt_mandoor" if k == n // 2 else ("tilt_louvre" if k % 2 else plain) for k in range(n)]
            else:
                cells = [plain] * n
        else:
            raise ValueError(f"unknown facade rule {rule!r}")
        out.append(cells)
    return out


def wall_levels(bottom, door_z, top, module_m, plain_h, grime_m=0.0):
    """the wall's level heights, ascending, and what each band between two of them is: ("found", z0, z1) under the door
    level (plain modules counted down from it), ("grime", ...) the band at the foot, ("module", ...) the door storey,
    ("plain", ...) above it. Levels closer than EPS_Z merge."""
    door_z = min(max(door_z, bottom), top)
    zs = [bottom]
    k = 1
    downs = []
    while door_z - k * plain_h > bottom + EPS_Z:
        downs.append(door_z - k * plain_h)
        k += 1
    zs += sorted(downs)
    if door_z > bottom + EPS_Z:
        zs.append(door_z)
    g = grime_m if grime_m and door_z + grime_m < min(top, door_z + module_m) - EPS_Z else 0.0
    if g:
        zs.append(door_z + g)
    mtop = door_z + module_m
    if mtop < top - EPS_Z:
        zs.append(mtop)
        z = mtop + plain_h
        while z < top - EPS_Z:
            zs.append(z)
            z += plain_h
    zs.append(top)
    bands = []
    for z0, z1 in zip(zs, zs[1:]):
        if z1 <= door_z + 1e-9:
            bands.append(("found", z0, z1))
        elif g and z0 < door_z + g - 1e-9:
            bands.append(("grime", z0, z1))
        elif z0 < mtop - 1e-9:
            bands.append(("module", z0, z1))
        else:
            bands.append(("plain", z0, z1))
    return zs, bands


def facade_walls(ring, skin, bottom, door_z, top, toward, grime_m=0.0, gable=None, parapet_m=0.0, cap_w=0.25):
    """Pure: the walls of one block in the atlas. ``ring`` counter-clockwise (x, y); ``toward`` a unit vector to the lap.
    ``gable`` = (ridge_z, (ux, uy)): the ridge's axis; the edges across it carry the gable ends up to the roof line (their
    roof line peaks at the edge's middle, as tools/author_bespoke_blend.py pitched_roof's box). ``parapet_m``: the walls carry
    on that far over ``top``, with a cap ``cap_w`` wide and the inner face back down to ``top`` (the flat_parapet form).
    Returns (verts, faces, uvs, info): every face shares its corners, the base ring first, in ring order."""
    sk = SKINS[skin]
    plain = sk["plain"]
    module_m = sk["module_m"]
    plain_h = CELLS[plain][4]
    n_e = len(ring)
    lengths = [math.dist(ring[i], ring[(i + 1) % n_e]) for i in range(n_e)]
    kinds = edge_kinds(ring, toward)
    cells = side_cells(skin, kinds, lengths)
    # the columns: every bay division of every edge, the ring's own corners included once
    cols, col_edge = [], []
    for i in range(n_e):
        a, b = ring[i], ring[(i + 1) % n_e]
        n = len(cells[i])
        for k in range(n):
            t = k / n
            cols.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
            col_edge.append((i, k))
    C = len(cols)
    wall_top = top + (parapet_m or 0.0)
    zs, bands = wall_levels(bottom, door_z, wall_top, module_m, plain_h, grime_m)
    verts = [(x, y, z) for z in zs for (x, y) in cols]
    faces, uvs = [], []
    grime_cell = sk.get("grime")
    door_z = min(max(door_z, bottom), wall_top)
    for li, (what, z0, z1) in enumerate(bands):
        for c in range(C):
            c1 = (c + 1) % C
            e, k = col_edge[c]
            cell = cells[e][k]
            if what == "found":
                # counted down from the door level: each band's top is its cell's top, so the tile carries on unbroken
                use, t0, t1 = plain, 1.0 - (z1 - z0) / plain_h, 1.0
            elif what == "grime":
                if CELLS[cell][5] or not grime_cell:
                    use, t0, t1 = cell, 0.0, (z1 - door_z) / module_m
                else:
                    # the whole grime cell over the band: its streaks fade out at the band's top, whatever its height
                    use, t0, t1 = grime_cell, 0.0, 1.0
            elif what == "module":
                use, t0, t1 = cell, (z0 - door_z) / module_m, (z1 - door_z) / module_m
            else:
                use, t0, t1 = plain, 0.0, (z1 - z0) / plain_h
            faces.append((li * C + c, li * C + c1, (li + 1) * C + c1, (li + 1) * C + c))
            uvs.append((atlas_uv(use, 0.0, t0), atlas_uv(use, 1.0, t0), atlas_uv(use, 1.0, t1), atlas_uv(use, 0.0, t1)))
    top_row = (len(zs) - 1) * C
    info = {"skin": skin, "bays": C, "levels": [round(z, 3) for z in zs],
            "openings": sum(1 for e in cells for q in e if q != plain)}
    if gable is not None:
        ridge_z, (rux, ruy) = gable
        gverts = {}
        n_gable = 0
        for c in range(C):
            e, k = col_edge[c]
            a, b = ring[e], ring[(e + 1) % n_e]
            L = lengths[e]
            dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
            if abs(dx * rux + dy * ruy) > 0.2:            # an eave side, not a gable end
                continue
            n = len(cells[e])
            s0, s1 = k / n * L, (k + 1) / n * L
            rise = ridge_z - top

            def line(s):
                return top + rise * (1.0 - abs(2.0 * s / L - 1.0))

            def vid(s):
                if line(s) <= top + 1e-6:
                    return top_row + (c if s <= s0 + 1e-9 else (c + 1) % C)
                key = (e, round(s, 6))
                if key not in gverts:
                    gverts[key] = len(verts)
                    verts.append((a[0] + dx * s, a[1] + dy * s, line(s)))
                return gverts[key]
            poly = [top_row + c, top_row + (c + 1) % C]
            pts = [s1]
            if s0 < L / 2 < s1:
                pts.append(L / 2)
            pts.append(s0)
            for s in pts:
                i_ = vid(s)
                if i_ not in poly:
                    poly.append(i_)
            if len(poly) < 3:
                continue
            span = max(plain_h, rise)
            faces.append(tuple(poly))
            uv = []
            for i_ in poly:
                x, y, z = verts[i_]
                s = (x - a[0]) * dx + (y - a[1]) * dy
                uv.append(atlas_uv(plain, (s - s0) / (s1 - s0), (z - top) / span))
            uvs.append(tuple(uv))
            n_gable += 1
        info["gable_faces"] = n_gable
    if parapet_m:
        cx, cy = sum(p[0] for p in ring) / n_e, sum(p[1] for p in ring) / n_e
        inset = []
        for x, y in cols:
            d = math.hypot(cx - x, cy - y) or 1.0
            inset.append((x + (cx - x) / d * cap_w, y + (cy - y) / d * cap_w))
        ti = len(verts)
        verts += [(x, y, wall_top) for x, y in inset]
        bi = len(verts)
        verts += [(x, y, top) for x, y in inset]
        for c in range(C):
            c1 = (c + 1) % C
            faces += [(top_row + c, top_row + c1, ti + c1, ti + c), (ti + c, ti + c1, bi + c1, bi + c)]
            uvs += [(atlas_uv(plain, 0, 0), atlas_uv(plain, 1, 0), atlas_uv(plain, 1, cap_w / plain_h), atlas_uv(plain, 0, cap_w / plain_h)),
                    (atlas_uv(plain, 0, parapet_m / plain_h), atlas_uv(plain, 1, parapet_m / plain_h), atlas_uv(plain, 1, 0), atlas_uv(plain, 0, 0))]
    return verts, faces, uvs, info


def gable_slab(c, u, v, hw, hh, eave, ridge_z, overhang, rake, fascia, tile, with_ends=False):
    """Pure: a gable roof as a slab with an eave overhang, a rake overhang and a fascia (ledger 0094; the depths are the
    block's own keys, [invented]). The box: centre ``c``, unit axes ``u`` (the ridge) and ``v``, half sizes ``hw`` / ``hh``;
    the roof's top plane passes through the wall line at ``eave`` and the ridge at ``ridge_z`` (as pitched_roof's), carried
    ``overhang`` past the eaves (so the eave edge drops by the pitch) and ``rake`` past the gable ends; the soffit is that plane
    ``fascia`` lower, and the fascia closes the edge. The top is cut at the wall line too, so ``with_ends`` stands the two gable
    triangles there (pitched_roof's own, for a skin whose walls stop at the eave) on the slab's own vertices. One shell. UVs in
    tiles of ``tile`` m: u along the eave, v up the slope from the wall line (negative over the overhang), as pitched_roof's"""
    k = (ridge_z - eave) / hh
    U, V = hw + rake, hh + overhang
    us = sorted({-U, -hw, hw, U})
    vs = sorted({-V, -hh, 0.0, hh, V})
    slope = math.sqrt(1.0 + k * k)

    def P(a, b, z):
        return (c[0] + u[0] * a + v[0] * b, c[1] + u[1] * a + v[1] * b, z)

    def zt(b):
        return eave + (hh - abs(b)) * k
    verts, idx = [], {}
    for layer, dz in (("t", 0.0), ("s", -fascia)):
        for a in us:
            for b in vs:
                idx[(layer, a, b)] = len(verts)
                verts.append(P(a, b, zt(b) + dz))
    faces, uvs = [], []

    def uv_of(a, b):
        return ((a + hw) / tile, (hh - abs(b)) * slope / tile)
    for i in range(len(us) - 1):
        for j in range(len(vs) - 1):
            a0, a1, b0, b1 = us[i], us[i + 1], vs[j], vs[j + 1]
            q = [("t", a0, b0), ("t", a1, b0), ("t", a1, b1), ("t", a0, b1)]
            faces.append(tuple(idx[x] for x in q))
            uvs.append(tuple(uv_of(x[1], x[2]) for x in q))
            s = [("s", a1, b0), ("s", a0, b0), ("s", a0, b1), ("s", a1, b1)]       # facing down
            faces.append(tuple(idx[x] for x in s))
            uvs.append(tuple(uv_of(x[1], x[2]) for x in s))
    f = fascia / tile
    # the fascia round the edge, each piece outward: (soffit a, soffit b, top b, top a) with a -> b keeping the outside on
    # the right (the box's frame is right-handed like x, y)
    ring = [(a, -V) for a in us] + [(U, b) for b in vs[1:]] + [(a, V) for a in reversed(us[:-1])] + [(-U, b) for b in reversed(vs[1:-1])]
    for (a0, b0), (a1, b1) in zip(ring, ring[1:] + ring[:1]):
        faces.append((idx[("s", a0, b0)], idx[("s", a1, b1)], idx[("t", a1, b1)], idx[("t", a0, b0)]))
        L = math.hypot(a1 - a0, b1 - b0) / tile
        uvs.append(((0.0, 0.0), (L, 0.0), (L, f), (0.0, f)))
    if with_ends:
        uv = ((0.0, 0.0), (2 * hh / tile, 0.0), (hh / tile, (ridge_z - eave) / tile))
        faces += [(idx[("t", hw, -hh)], idx[("t", hw, hh)], idx[("t", hw, 0.0)]),
                  (idx[("t", -hw, hh)], idx[("t", -hw, -hh)], idx[("t", -hw, 0.0)])]
        uvs += [uv, uv]
    return verts, faces, uvs


def rooftop_box(cx, cy, w, d, h, ux, uy, z0):
    """Pure: a rooftop unit (ledger 0094 rooftop_units): a box w along (ux, uy), d across it, h tall, standing on z0; four
    sides in the atlas's rtu_side cell (one cell per whole RTU_BAY_M bay, the module stretched to the box's height), its top
    in metal_plain. No bottom. Returns (verts, faces, uvs), one island"""
    vx, vy = -uy, ux
    corners = [(-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2)]
    ring = [(cx + ux * a + vx * b, cy + uy * a + vy * b) for a, b in corners]
    cols = []
    for i in range(4):
        a, b = ring[i], ring[(i + 1) % 4]
        n = bays(math.dist(a, b), RTU_BAY_M)
        cols += [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(n)]
    C = len(cols)
    verts = [(x, y, z0) for x, y in cols] + [(x, y, z0 + h) for x, y in cols]
    faces, uvs = [], []
    for k in range(C):
        k1 = (k + 1) % C
        faces.append((k, k1, C + k1, C + k))
        uvs.append((atlas_uv("rtu_side", 0, 0), atlas_uv("rtu_side", 1, 0), atlas_uv("rtu_side", 1, 1), atlas_uv("rtu_side", 0, 1)))
    top = list(range(C, 2 * C))
    faces.append(tuple(top))
    uv_top = []
    for i in top:
        x, y, _ = verts[i]
        a = ((x - cx) * ux + (y - cy) * uy) / w + 0.5
        b = ((x - cx) * vx + (y - cy) * vy) / d + 0.5
        uv_top.append(atlas_uv("metal_plain", a, b))
    uvs.append(tuple(uv_top))
    return verts, faces, uvs

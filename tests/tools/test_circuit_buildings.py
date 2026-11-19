"""Ledger 0094 (Kevin 2026-11-18: "the buildings are all flat on milford and high plains"): the facade atlas and the roof /
tent normals tools/make_bespoke_assets.py's third batch paints, tools/circuit_facades.py's pure walls / slab / rooftop units,
the author tool's row check, and the two circuits' opt-in config. Plain test_* functions; bpy and mathutils are stubbed."""
from __future__ import annotations

import importlib.util
import json
import math
import sys
import types
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
TEX = ROOT / "assets" / "textures"
sys.path.insert(0, str(ROOT / "tools"))

import circuit_facades as cf  # noqa: E402

MILFORD = ROOT / "tracks" / "milford-road-course-lm"
HP = ROOT / "tracks" / "high-plains-lm"
NEW = ("circuit_facade_diffuse.jpg", "circuit_facade_normal.jpg", "roof_membrane_normal.jpg", "roof_rib_normal.jpg",
       "fabric_tent_diffuse.jpg", "fabric_tent_normal.jpg")


def _author():
    for name in ("bpy", "mathutils", "mathutils.bvhtree"):
        sys.modules.setdefault(name, types.ModuleType(name))
    sys.modules["mathutils"].Vector = object
    sys.modules["mathutils.bvhtree"].BVHTree = object
    spec = importlib.util.spec_from_file_location("author_bespoke_blend_0094", ROOT / "tools" / "author_bespoke_blend.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _tilt(path):
    n = np.asarray(Image.open(path).convert("RGB")).astype(float) / 127.5 - 1.0
    nz = n[..., 2] / np.linalg.norm(n, axis=-1)
    return np.degrees(np.arccos(np.clip(nz, -1.0, 1.0)))


def _pot(n):
    return n > 0 and n & (n - 1) == 0


def test_new_textures_are_power_of_two_and_within_the_byte_budget():
    for f in NEW:
        p = TEX / f
        w, h = Image.open(p).size
        assert _pot(w) and _pot(h) and max(w, h) <= 2048, (f, w, h)
        assert p.stat().st_size <= 2_000_000, (f, p.stat().st_size)    # tools/make_kerb_texture.py MAX_BYTES (V1 d)
    assert Image.open(TEX / cf.ATLAS_DIFFUSE).size == (cf.ATLAS_PX, cf.ATLAS_PX)


def test_the_new_files_are_licensed_cc0_and_listed_by_the_generator():
    gen = importlib.util.spec_from_file_location("mba_0094", ROOT / "tools" / "make_bespoke_assets.py")
    mod = importlib.util.module_from_spec(gen)
    gen.loader.exec_module(mod)
    assert tuple(mod.CIRCUIT_FILES) == NEW and set(NEW) <= set(mod.TEX_FILES)
    lic = json.loads((ROOT / "assets" / "licenses.json").read_text(encoding="utf-8"))
    rows = [a for a in lic["bundled_assets"] if cf.ATLAS_DIFFUSE in a.get("files", [])]
    assert len(rows) == 1 and set(rows[0]["files"]) == set(NEW)
    assert rows[0]["license"] == "CC0-1.0" and "make_bespoke_assets.py" in rows[0]["source"]


def test_cells_sit_inside_their_slots_and_never_overlap():
    seen = []
    for name in cf.CELLS:
        x0, y0, x1, y1 = cf.cell_px(name)
        assert 0 <= x0 - cf.PAD_PX and x1 + cf.PAD_PX <= cf.ATLAS_PX and 0 <= y0 - cf.PAD_PX and y1 + cf.PAD_PX <= cf.ATLAS_PX, name
        for other, (a0, b0, a1, b1) in seen:
            assert x1 + cf.PAD_PX <= a0 or a1 + cf.PAD_PX <= x0 or y1 + cf.PAD_PX <= b0 or b1 + cf.PAD_PX <= y0, (name, other)
        seen.append((name, (x0, y0, x1, y1)))
        u0, v0, u1, v1 = cf.cell_uv(name)
        assert 0 < u0 < u1 < 1 and 0 < v0 < v1 < 1


def test_the_ribs_have_real_relief_and_the_old_metal_was_flat():
    """the audit measured the old metal_wall_normal at 0.3 / 2.1 deg (p50 / p90); the new rib faces stand at 45-60 deg"""
    t = _tilt(TEX / cf.ATLAS_NORMAL)
    for name in ("metal_plain", "container_side_tan"):
        x0, y0, x1, y1 = cf.cell_px(name)
        rows = t[y0 + 40:y0 + 60, x0:x1]
        peaks = rows.max(axis=1)
        assert np.all((peaks >= 45.0) & (peaks <= 62.0)), (name, peaks)
        assert np.percentile(rows, 90) > 30.0, name
    rib = _tilt(TEX / "roof_rib_normal.jpg")[100]
    assert 45.0 <= rib.max() <= 62.0
    assert np.percentile(_tilt(TEX / "metal_wall_normal.jpg"), 90) < 5.0


def test_every_opening_cell_shows_its_opening():
    """a door / window / louvre cell differs from its family's plain cell where the opening is drawn"""
    d = np.asarray(Image.open(TEX / cf.ATLAS_DIFFUSE).convert("RGB")).astype(float)

    def cell(n):
        x0, y0, x1, y1 = cf.cell_px(n)
        return d[y0:y1, x0:x1]
    for name, plain in (("metal_rollup", "metal_plain"), ("metal_mandoor", "metal_plain"), ("metal_window", "metal_plain"),
                        ("tilt_dock", "tilt_plain"), ("tilt_mandoor", "tilt_plain"), ("tilt_louvre", "tilt_plain"),
                        ("container_doors_tan", "container_side_tan")):
        diff = np.abs(cell(name) - cell(plain)).mean(axis=2)
        assert (diff > 40).mean() > 0.01, name
    lum = d.mean(axis=2)
    for name in ("metal_rollup", "tilt_dock"):
        x0, y0, x1, y1 = cf.cell_px(name)
        assert lum[y0:y1, x0:x1].std() > 20.0, name       # the old tiltup tile's luminance sd was 12.1 (the audit)


def test_bays_keep_every_opening_whole():
    for w in (cf.METAL_BAY_M, cf.TILT_BAY_M, cf.CONTAINER_SIDE_M):
        for L in np.linspace(0.8 * w, 40 * w, 157):
            n = cf.bays(L, w)
            assert n >= 1 and 0.66 <= (L / n) / w <= 1.6, (w, L, n)


def _islands(nv, faces):
    parent = list(range(nv))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for f in faces:
        for a, b in zip(f, f[1:] + f[:1]):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb
    return len({find(i) for f in faces for i in f})


def _inside_some_cell(uv):
    for name in cf.CELLS:
        u0, v0, u1, v1 = cf.cell_uv(name)
        if u0 - 1e-9 <= uv[0] <= u1 + 1e-9 and v0 - 1e-9 <= uv[1] <= v1 + 1e-9:
            return True
    return False


def test_walls_are_one_island_with_the_base_ring_first():
    """engine-july's prep re-seats a building by island and reads its base ring as the vertices at its lowest z, in index
    order: the atlas walls must stay one island, their base ring first and in ring order"""
    ring = [(0.0, 0.0), (70.1, 0.0), (70.1, 7.5), (0.0, 7.5)]
    v, f, uv, info = cf.facade_walls(ring, "garage", 0.0, 0.0, 2.6, (0.0, -1.0), grime_m=0.5, gable=(3.6, (1.0, 0.0)))
    assert _islands(len(v), f) == 1
    zmin = min(p[2] for p in v)
    base = [i for i, p in enumerate(v) if p[2] < zmin + 0.05]
    assert base == list(range(info["bays"]))
    assert all(_inside_some_cell(q) for face in uv for q in face)
    assert max(p[2] for p in v) == 3.6 and info["gable_faces"] >= 2
    # the front (facing the lap, -y here) is all roll-up doors, the back has man doors
    kinds = cf.edge_kinds(ring, (0.0, -1.0))
    cells = cf.side_cells("garage", kinds, [70.1, 7.5, 70.1, 7.5])
    assert set(cells[0]) == {"metal_rollup"} and len(cells[0]) == cf.bays(70.1, cf.METAL_BAY_M)
    assert "metal_mandoor" in cells[2] and "metal_rollup" not in cells[2]


def test_a_tall_far_wall_carries_plain_modules_and_its_foundation():
    ring = [(0.0, 0.0), (150.0, 0.0), (150.0, 90.0), (0.0, 90.0)]
    v, f, uv, info = cf.facade_walls(ring, "plant", -4.15, 0.0, 13.0, (1.0, 0.0), grime_m=0.8)
    assert info["levels"][0] == -4.15 and 0.0 in info["levels"] and 0.8 in info["levels"] and 8.0 in info["levels"]
    assert info["levels"][-1] == 13.0
    assert _islands(len(v), f) == 1
    cells = cf.side_cells("plant", cf.edge_kinds(ring, (1.0, 0.0)), [150.0, 90.0, 150.0, 90.0])
    long_side = cells[0]
    assert long_side[0] == long_side[-1] == "tilt_mandoor" and "tilt_dock" in long_side
    assert "tilt_dock" not in (long_side[0], long_side[-1])


def test_a_parapet_and_a_post_and_a_container():
    ring = [(0.0, 0.0), (20.0, 0.0), (20.0, 12.0), (0.0, 12.0)]
    v, f, uv, _ = cf.facade_walls(ring, "plant", 0.0, 0.0, 6.0, (0.0, -1.0), parapet_m=0.9)
    assert max(p[2] for p in v) == 6.9 and _islands(len(v), f) == 1
    post = [(0.0, 0.0), (3.5, 0.0), (3.5, 3.5), (0.0, 3.5)]
    cells = cf.side_cells("post", cf.edge_kinds(post, (0.0, -1.0)), [3.5] * 4)
    assert cells[0] == ["metal_window"] and cells[2] == ["metal_mandoor"]
    box = [(0.0, 0.0), (12.8, 0.0), (12.8, 4.5), (0.0, 4.5)]
    cells = cf.side_cells("container_tan", cf.edge_kinds(box, (1.0, 0.0)), [12.8, 4.5, 12.8, 4.5])
    assert cells[1] == ["container_doors_tan"] * 2 and set(cells[3]) == {"container_side_tan"}


def test_the_gable_slab_overhangs_and_closes():
    c, u, v = (0.0, 0.0), (1.0, 0.0), (0.0, 1.0)
    verts, faces, uvs = cf.gable_slab(c, u, v, 35.05, 3.75, 2.6, 3.6, 0.3, 0.3, 0.2, 12.0)
    xs, ys, zs = [p[0] for p in verts], [p[1] for p in verts], [p[2] for p in verts]
    assert math.isclose(max(xs), 35.35) and math.isclose(max(ys), 4.05)
    assert math.isclose(min(zs), 2.6 - 0.3 * (1.0 / 3.75) - 0.2)
    edges = {}
    for fc in faces:
        for a, b in zip(fc, fc[1:] + fc[:1]):
            edges[frozenset((a, b))] = edges.get(frozenset((a, b)), 0) + 1
    assert set(edges.values()) == {2}, "a closed slab: every edge shared by two faces"
    assert _islands(len(verts), faces) == 1
    _, faces2, _ = cf.gable_slab(c, u, v, 35.05, 3.75, 2.6, 3.6, 0.3, 0.3, 0.2, 12.0, with_ends=True)
    assert len(faces2) == len(faces) + 2


def test_a_rooftop_unit_stands_on_the_roof():
    verts, faces, uvs = cf.rooftop_box(10.0, 5.0, 10.2, 12.7, 1.5, math.cos(0.7), math.sin(0.7), 24.25)
    assert min(p[2] for p in verts) == 24.25 and max(p[2] for p in verts) == 25.75
    assert _islands(len(verts), faces) == 1 and all(_inside_some_cell(q) for face in uvs for q in face)


def test_the_row_check_refuses_a_mix_and_an_unbound_row():
    m = _author()
    atlas = {"diffuse": f"assets/textures/{cf.ATLAS_DIFFUSE}", "normal": f"assets/textures/{cf.ATLAS_NORMAL}"}
    old = {"diffuse": "assets/textures/metal_wall_diffuse.jpg", "normal": "assets/textures/metal_wall_normal.jpg"}
    assert m.atlas_rows_check({"BUILDING_METAL"}, set(), {"BUILDING_METAL": atlas}) == []
    assert m.atlas_rows_check(set(), {"BUILDING_METAL"}, {"BUILDING_METAL": old}) == []
    assert m.atlas_rows_check(set(), {"BUILDING_METAL"}, {}) == []                 # every track before this ledger
    assert m.atlas_rows_check({"BUILDING_METAL"}, set(), {"BUILDING_METAL": old})
    assert m.atlas_rows_check({"BUILDING_METAL"}, {"BUILDING_METAL"}, {"BUILDING_METAL": atlas})
    assert m.atlas_rows_check(set(), {"FARBLOCK_TILTUP"}, {"FARBLOCK_TILTUP": atlas})
    assert m.block_opt({"a": 1}, {"file": "x", "a": 2}, "a") == 1
    assert m.block_opt({}, {"file": "x", "a": 2}, "a") == 2
    assert m.block_opt({}, {"a": 2}, "a") is None                                  # an inline block is its own group


def _rows(track):
    cfg = json.loads((track / "track.config.json").read_text(encoding="utf-8"))
    return cfg, cfg["scenery"]["bespoke"]["blocks"]


def test_milford_wears_the_atlas_and_every_bound_file_exists():
    cfg, groups = _rows(MILFORD)
    ov = cfg["texture_overrides"]
    for row in ("BUILDING_METAL", "FARBLOCK_METAL", "FARBLOCK_TILTUP"):
        assert Path(ov[row]["diffuse"]).name == cf.ATLAS_DIFFUSE and Path(ov[row]["normal"]).name == cf.ATLAS_NORMAL, row
    for row in ("ROOFTOP_WHITE", "ROOFTOP_TAN"):
        assert Path(ov[row]["normal"]).name == "roof_membrane_normal.jpg"
    assert Path(ov["BUILDING_FABRIC"]["diffuse"]).name == "fabric_tent_diffuse.jpg"
    ship = json.loads((MILFORD / "ship.json").read_text(encoding="utf-8"))
    listed = set(ship["sync_in"].get("assets", [])) | set(ship["sync_in"]["required"])
    for o in ov.values():
        for k in ("diffuse", "normal"):
            if o.get(k) and (Path(o[k]).name in NEW or o[k].startswith("source/")):
                assert (ROOT / o[k]).exists() or (MILFORD / o[k]).exists(), o[k]
                assert o[k] in listed, o[k]                              # the workshop gets what the new rows bind
    assert Path(ov["ROOF"]["diffuse"]).name == "roof_naip_palette.png"   # the measured colours (item 4)
    skins = {}
    for g in groups:
        items = json.loads((MILFORD / g["file"]).read_text(encoding="utf-8")) if g.get("file") else [g]
        for b in items:
            own = b.get("skin", "tiltup")
            skins[b["key"]] = own if own in cf.SKINS or not (g.get("file") and g.get("skin")) else g["skin"]
    assert all(s in cf.SKINS for s in skins.values()), skins
    assert skins["pad_shed_north"] == "container_tan" and skins["pad_shed_south"] == "container_white"
    assert len(skins) == 25


def test_milford_rooftop_units_stand_inside_their_roofs():
    units = json.loads((MILFORD / "source/furniture/rooftop/rooftop_units.json").read_text(encoding="utf-8"))
    _, groups = _rows(MILFORD)
    rings = {}
    for g in groups:
        for b in (json.loads((MILFORD / g["file"]).read_text(encoding="utf-8")) if g.get("file") else [g]):
            rings[b["key"]] = b["footprint_lonlat"]
    assert units["mpg_plant_a"] and units["mpg_plant_b"]
    for key, us in units.items():
        ring = rings[key]
        for q in us:
            x, y = q["lonlat"]
            inside = False
            for i in range(len(ring)):
                (ax, ay), (bx, by) = ring[i], ring[(i + 1) % len(ring)]
                if (ay > y) != (by > y) and x < ax + (y - ay) * (bx - ax) / (by - ay):
                    inside = not inside
            assert inside, (key, q)
            assert 1.0 <= q["w_m"] <= 30.0 and 1.0 <= q["d_m"] <= 30.0 and "[invented]" in q["_source"]


def test_high_plains_wears_the_atlas_on_its_metal_rows_only():
    cfg, groups = _rows(HP)
    ov = cfg["texture_overrides"]
    for row in ("BUILDING_METAL", "FARBLOCK_METAL"):
        assert Path(ov[row]["diffuse"]).name == cf.ATLAS_DIFFUSE, row
    assert "BUILDING_TILTUP" not in ov and "FARBLOCK_TILTUP" not in ov
    for row in ("ROOFTOP_WHITE", "ROOFTOP_TAN", "ROOFTOP_DARK"):
        assert Path(ov[row]["normal"]).name == "roof_rib_normal.jpg"
    m = _author()
    assert Path(ov[m.CANOPY_SPARE_ROW]["diffuse"]).name == m.CANOPY_SKIN, "the canopies keep their ribbed metal"
    by_file = {Path(g["file"]).name: g for g in groups if g.get("file")}
    assert by_file["buildings.race.json"]["skin"] == "garage" and by_file["posts.race.json"]["skin"] == "post"
    rows = {r["key"]: r for r in json.loads((HP / "source/bespoke/buildings.race.json").read_text(encoding="utf-8"))}
    carport, canopy = rows["osm289311821"], rows["traced_pit_entry_canopy"]
    assert carport["form"] == "posts" and carport["canopy_roof"] == "gable" and carport["post_collider"] is True
    assert canopy["form"] == "posts" and canopy["post_collider"] is True
    assert rows["traced_container_row"]["skin"] == "container_row"
    walled = [r for r in rows.values() if r.get("form") != "posts"]
    assert all(r.get("skin", "metal") in cf.SKINS or by_file["buildings.race.json"]["skin"] in cf.SKINS for r in walled)


def test_a_container_row_is_ten_boxes_doors_to_the_lap():
    ring = [(0.0, 0.0), (24.9, 0.0), (24.9, 12.2), (0.0, 12.2)]
    cells = cf.side_cells("container_row", cf.edge_kinds(ring, (0.0, -1.0)), [24.9, 12.2, 24.9, 12.2])
    assert len(cells[0]) == 10 and all(c.startswith("container_doors_") for c in cells[0])
    front = [c.rsplit("_", 1)[1] for c in cells[0]]
    back = [c.rsplit("_", 1)[1] for c in cells[2]]
    assert back == front[::-1], "a box wears one colour front and back"
    assert set(cells[1]) == {f"container_side_{front[-1]}"} and set(cells[3]) == {f"container_side_{front[0]}"}


def test_post_squares_are_the_posts_canopy_on_posts_stands():
    m = _author()
    ring = [(0.0, 0.0), (70.1, 0.0), (70.1, 7.5), (0.0, 7.5)]
    for step in (m.CANOPY_POST_M, 4.39):
        v, f, u, n = m.canopy_on_posts(ring, 0.0, 2.55, slab=0.15, step=step)
        sq = m.canopy_post_squares(ring, step=step)
        assert len(sq) == n
        feet = [p for p in v if p[2] == 0.0]
        assert len(feet) == 4 * n
        for q in sq:
            for x, y in q:
                assert any(abs(x - a) < 1e-9 and abs(y - b) < 1e-9 for a, b, _ in feet)
    assert len(m.canopy_post_squares(ring, step=4.39)) == 2 * 16 + 2 * 2      # a post between every two of the 16 stalls


def test_a_post_collider_stands_inside_its_post_on_its_own_ground():
    m = _author()
    q = m.canopy_post_squares([(0.0, 0.0), (9.5, 0.0), (9.5, 8.1), (0.0, 8.1)])[0]
    qi = m.inset_square(q, m.COLLIDER_INSET_M)
    xs, ys = [p[0] for p in q], [p[1] for p in q]
    for x, y in qi:                                           # a hair inside every face of the visible post
        assert min(xs) < x < max(xs) and min(ys) < y < max(ys)
        assert min(x - min(xs), max(xs) - x, y - min(ys), max(ys) - y) > 0.015
    feet = [10.0, 10.1, 10.2, 10.05]
    v, f, u = m.post_collider(qi, [g - m.BOTTOM_UNDER_M for g in feet], 13.0)
    assert [round(p[2], 6) for p in v[:4]] == [round(g - m.BOTTOM_UNDER_M, 6) for g in feet]
    assert all(p[2] == 13.0 for p in v[4:]) and len(f) == 4 and _islands(len(v), f) == 1
    cx, cy = sum(p[0] for p in qi) / 4, sum(p[1] for p in qi) / 4
    for face in f:                                            # every side faces out of the post
        a, b, c = (v[i] for i in face[:3])
        n = ((b[1] - a[1]) * (c[2] - a[2]) - (b[2] - a[2]) * (c[1] - a[1]), (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2]))
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        assert n[0] * (mx - cx) + n[1] * (my - cy) > 0


def test_post_colliders_follow_the_fine_ground_rule():
    m = _author()
    ring = [(0.0, 0.0), (9.5, 0.0), (9.5, 8.1), (0.0, 8.1)]
    calls = []

    def fine(tree, x, y):
        calls.append((x, y))
        return 4.0
    real_edge, real_down = m.down_edge, m.down
    try:
        m.down_edge, m.down = fine, (lambda tree, x, y: 100.0 + 0.01 * x)
        boxes, why = m.canopy_post_colliders(ring, m.CANOPY_POST_M, 103.0, object(), m.COLLIDER_TRI_M)
        assert why is None and len(boxes) == len(m.canopy_post_squares(ring)) == 8
        assert all(min(p[2] for p in v) < 100.0 + 0.01 * 9.5 - m.BOTTOM_UNDER_M + 1e-9 for v, _, _ in boxes)
        m.down_edge = lambda tree, x, y: 12.3 if x > 9.0 else 4.0          # one post over a coarse triangle
        boxes, why = m.canopy_post_colliders(ring, m.CANOPY_POST_M, 103.0, object(), m.COLLIDER_TRI_M)
        assert boxes == [] and "post" in why
        boxes, why = m.canopy_post_colliders(ring, m.CANOPY_POST_M, 103.0, object(), 14.0)   # High Plains' posts group limit
        assert why is None and len(boxes) == 8
        m.down = lambda tree, x, y: None if y > 8.0 else 100.0                # a post off the ground
        boxes, why = m.canopy_post_colliders(ring, m.CANOPY_POST_M, 103.0, object(), 14.0)
        assert boxes == [] and why
    finally:
        m.down_edge, m.down = real_edge, real_down


def test_the_existing_skins_are_untouched():
    """Lake Murray and every other track bind the old files: their bytes are the committed ones (md5 of the blob git
    tracks, CRLF-free binaries)"""
    want = {"metal_wall_diffuse.jpg": 17897, "metal_wall_normal.jpg": 3560, "tiltup_wall_diffuse.jpg": 27168,
            "tiltup_wall_normal.jpg": 43360, "roof_white_diffuse.jpg": 6467, "roof_tan_diffuse.jpg": 5128,
            "roof_dark_diffuse.jpg": 3493}
    for f, size in want.items():
        assert (TEX / f).stat().st_size == size, f

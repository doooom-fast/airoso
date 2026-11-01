"""The bespoke dressing (.claude/skills/bespoke-assets, first batch): the generators reproduce the committed bytes, what AC
refuses is refused here (L7), every prefix the author tool makes binds a texture and survives the prep, the cone plan's
rule, and Nevada Nights' declaration. Plain test_* functions, no bpy."""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.ac import pbr  # noqa: E402

TRACK = ROOT / "tracks" / "exotics-racing-lv"


def _tool(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


gen = _tool("make_bespoke_assets")
plan = _tool("plan_cones")


def _pot(n):
    return n > 0 and n & (n - 1) == 0


def test_generator_reproduces_the_committed_files():
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "make_bespoke_assets.py"), "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_textures_are_power_of_two_and_within_the_cap():
    files = [gen.TEX / f for f in gen.TEX_FILES] + [TRACK / "textures" / "caliche_diffuse.jpg", TRACK / "textures" / "caliche_normal.jpg"]
    for f in files:
        w, h = Image.open(f).size
        assert _pot(w) and _pot(h) and max(w, h) <= 2048, f"{f.name}: {w}x{h}"


def test_scrub_atlas_cuts_out_and_stays_in_its_cells():
    a = Image.open(gen.TEX / "desert_scrub_atlas.png")
    assert a.mode == "RGBA"
    alpha = a.getchannel("A")
    assert alpha.getextrema() == (0, 255)
    n = a.width
    # every cell has a plant, and the plant stands on the cell's bottom edge
    for row in range(2):
        for col in range(2):
            cell = alpha.crop((col * n // 2, row * n // 2, (col + 1) * n // 2, (row + 1) * n // 2))
            box = cell.getbbox()
            assert box is not None and box[3] >= n // 2 - 3, (row, col, box)


def test_cone_is_a_standard_cone_under_budget():
    spec = json.loads((gen.MODELS / "traffic_cone.json").read_text(encoding="utf-8"))
    assert abs(spec["height_m"] - 28 * 0.0254) < 1e-3
    lines = (gen.MODELS / "traffic_cone.obj").read_text(encoding="utf-8").splitlines()
    verts = [tuple(map(float, ln.split()[1:])) for ln in lines if ln.startswith("v ")]
    assert len(verts) == spec["vertices"] < 64
    assert min(v[1] for v in verts) == 0.0, "base at y = 0"
    assert abs(max(v[1] for v in verts) - spec["height_m"]) < 1e-3


def test_cone_faces_point_outward():
    lines = (gen.MODELS / "traffic_cone.obj").read_text(encoding="utf-8").splitlines()
    v = [tuple(map(float, ln.split()[1:])) for ln in lines if ln.startswith("v ")]
    for ln in lines:
        if not ln.startswith("f "):
            continue
        ix = [int(q.split("/")[0]) - 1 for q in ln.split()[1:]]
        a, b, c = v[ix[0]], v[ix[1]], v[ix[2]]
        u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
        w = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
        n = (u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0])
        mid = [sum(v[i][k] for i in ix) / len(ix) for k in range(3)]
        centre = (0.0, 0.2, 0.0)
        outward = sum(n[k] * (mid[k] - centre[k]) for k in range(3))
        assert outward > 0, ln


def test_every_author_prefix_binds_its_own_row_and_a_real_texture():
    for name, key in (("BUILDING_FABRIC_a", "BUILDING_FABRIC"), ("1WALL_FABRIC_a", "1WALL_FABRIC"),
                      ("PROPCONE_0", "PROPCONE"), ("SCRUBCARD_0", "SCRUBCARD")):
        r = pbr.resolve(name)
        assert r["key"] == key, (name, r["key"])
        assert r["diffuse"] is not None and r["diffuse"].exists(), name      # L7: a texture-less material renders black
    assert "SCRUBCARD" in pbr.BILLBOARD and "SCRUBCARD" in pbr.KS_PROPS
    assert pbr.resolve("BUILDING_a")["key"] == "BUILDING" and pbr.resolve("SCRUB_a")["key"] == "SCRUB"


def test_the_prep_keeps_their_uvs_and_never_welds_their_shells():
    text = (ROOT / "scripts" / "ac" / "build_kn5_loop.py").read_text(encoding="utf-8")
    planar = re.search(r"startswith\(\(([^)]*)\)\):\s*planar_uv\(me\)", text).group(1)
    weld = re.search(r"startswith\(\(([^)]*)\)\):\s*bmesh\.ops\.remove_doubles\(bm, verts=bm\.verts, dist=1e-4\)", text).group(1)
    for p in ("BUILDING_FABRIC", "1WALL_FABRIC", "PROPCONE", "SCRUB"):
        assert f'"{p}"' in planar, p
    for p in ("BUILDING_FABRIC", "PROPCONE", "SCRUB", "1WALL"):
        assert f'"{p}"' in weld, p


def _circle_lap(r, step=3.0):
    import math
    n = int(2 * math.pi * r / step)
    return [(r * math.cos(2 * math.pi * k / n), 0.0, r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def test_plan_cones_finds_nothing_on_a_straight_and_keeps_sides_by_turn():
    import math
    straight = [(0.0, 0.0, 3.0 * k) for k in range(200)] + [(0.0, 0.0, 3.0 * (199 - k)) for k in range(200)]
    assert plan.signed_curvature(straight)[100] == 0.0
    # a stadium driven counter-clockwise (x = E, z = N): every corner turns left, so the apex is on the left
    pts = []
    for k in range(120):
        pts.append((3.0 * k, 0.0, 0.0))
    for k in range(40):
        a = -math.pi / 2 + math.pi * k / 40
        pts.append((360 + 40 * math.cos(a), 0.0, 40 + 40 * math.sin(a)))
    for k in range(120):
        pts.append((360 - 3.0 * k, 0.0, 80.0))
    for k in range(40):
        a = math.pi / 2 + math.pi * k / 40
        pts.append((40 * math.cos(a), 0.0, 40 + 40 * math.sin(a)))
    st, rows = plan.stations(pts)
    assert len(rows) == 2 and all(r["turn"] == "L" for r in rows)
    assert {s["side"] for s in st if s["role"] == "apex"} == {"L"}
    assert {s["side"] for s in st if s["role"] in ("brake", "exit")} == {"R"}
    assert sorted(s["role"] for s in st) == ["apex", "apex", "brake", "brake", "exit", "exit"]


def test_nevada_nights_declaration():
    cfg = json.loads((TRACK / "track.config.json").read_text(encoding="utf-8"))
    b = cfg["scenery"]["bespoke"]
    assert [x["key"] for x in b["buildings"]] == ["exr2013_a", "exr2013_b"], "as in 2013: two buildings, no Welcome Center"
    assert all(len(x["footprint_lonlat"]) == 4 and x["_source"] for x in b["buildings"])
    assert b["scrub"]["count"] > 0 and b["cones"]["stations"]
    ship = json.loads((TRACK / "ship.json").read_text(encoding="utf-8"))
    assert ship["steps"]["author"] == ["bespoke"] and "house_seat" in ship["steps"]["gate"]
    for key in ("1GRASS", "GRASS_FAR", "SHOULDERUND"):
        o = cfg["texture_overrides"][key]
        assert o["diffuse"] in ship["sync_in"]["optional"] and (TRACK / o["diffuse"]).exists()


def test_the_second_batch_binds_its_own_rows():
    for name, key in (("BUILDING_TILTUP_0", "BUILDING_TILTUP"), ("BUILDING_METAL_0", "BUILDING_METAL"), ("BUILDING_DRYSTONE_0", "BUILDING_DRYSTONE"),
                      ("FARBLOCK_TILTUP_0", "FARBLOCK_TILTUP"), ("FARBLOCK_METAL_0", "FARBLOCK_METAL"), ("ROOFTOP_WHITE_0", "ROOFTOP_WHITE"),
                      ("ROOFTOP_TAN_0", "ROOFTOP_TAN"), ("ROOFTOP_DARK_0", "ROOFTOP_DARK"), ("1WALL_TILTUP_0", "1WALL_TILTUP"),
                      ("1WALL_TECPRO_0", "1WALL_TECPRO"), ("1WALL_KRAILBW_0", "1WALL_KRAILBW"), ("1WALL_GHOST_1WALL_PARA_stone", "1WALL_GHOST"),
                      ("PADAPRON_0", "PADAPRON"), ("GUARDRAIL_0", "GUARDRAIL"), ("TREECARD_0", "TREECARD"),
                      ("TREECARD_CONIFER_0", "TREECARD_CONIFER"), ("PRAIRIECARD_0", "PRAIRIECARD")):
        r = pbr.resolve(name)
        assert r["key"] == key, (name, r["key"])
        assert r["diffuse"] is not None and r["diffuse"].exists(), name
    for key in ("TREECARD", "TREECARD_CONIFER", "PRAIRIECARD", "1WALL_GHOST"):
        assert key in pbr.BILLBOARD, key
    assert pbr.resolve("BUILDING_a")["key"] == "BUILDING", "the existing buildings keep their row"


def test_the_ghost_is_fully_transparent():
    assert Image.open(gen.TEX / "ghost_alpha.png").getchannel("A").getextrema() == (0, 0)


def test_the_second_batch_keeps_its_uvs_through_the_prep():
    text = (ROOT / "scripts" / "ac" / "build_kn5_loop.py").read_text(encoding="utf-8")
    planar = re.search(r"startswith\(\(([^)]*)\)\):\s*planar_uv\(me\)", text).group(1)
    weld = re.search(r"startswith\(\(([^)]*)\)\):\s*bmesh\.ops\.remove_doubles\(bm, verts=bm\.verts, dist=1e-4\)", text).group(1)
    for q in ("BUILDING_TILTUP", "BUILDING_METAL", "BUILDING_DRYSTONE", "FARBLOCK", "ROOFTOP", "1WALL_TILTUP", "1WALL_TECPRO", "1WALL_KRAILBW", "GUARDRAIL", "PADAPRON"):
        assert f'"{q}"' in planar, q
    for q in ("BUILDING_TILTUP", "BUILDING_METAL", "FARBLOCK", "GUARDRAIL"):
        assert f'"{q}"' in weld, q


def test_a_far_backdrop_never_occludes_grassfx_and_a_pad_does():
    text = (ROOT / "scripts" / "ac" / "ext_config.py").read_text(encoding="utf-8")
    prefixes = re.search(r"OCCLUDE_PREFIXES = \(([^)]*)\)", text).group(1)
    assert '"PADAPRON"' in prefixes
    assert "FARBLOCK" not in prefixes and "ROOFTOP" not in prefixes
    assert "BUILDING_TILTUP".startswith("BUILDING") and not "FARBLOCK_TILTUP".startswith("BUILDING")


def test_grassfx_rectangles_cover_their_cells_once():
    gf = _tool("plan_grassfx_aerial")
    cells = {(i, j) for i in range(5) for j in range(3)} | {(7, 0), (8, 0), (7, 1)}
    out = gf.rects(cells)
    seen = []
    for i, j, w, h in out:
        seen += [(a, b) for a in range(i, i + w) for b in range(j, j + h)]
    assert sorted(seen) == sorted(cells), "every cell once"
    assert out[0][2] * out[0][3] == 15, "the biggest first"


def test_the_veg_planner_reads_both_frames():
    veg = _tool("plan_bespoke_vegetation")
    f = veg.geo({"bbox_lonlat": [-1.0, 0.0, 1.0, 2.0]}, 200, 100)
    assert f(0.0, 1.0) == (100.0, 50.0)
    g = veg.geo({"webmerc": {"z": 1, "x0": 0, "y0": 0}}, 512, 512)
    x, y = g(0.0, 0.0)
    assert abs(x - 256) < 1e-6 and abs(y - 256) < 1e-6


def test_milford_is_on_the_true_frame():
    """the USGS export has square-degree pixels (source/trace/unsquash_frame.py): the lap reaches 42.5741 N, 4.9 km round"""
    fixes = json.loads((ROOT / "tracks" / "milford-road-course" / "source" / "mrc_fixes.json").read_text(encoding="utf-8"))
    lats = [q["lat"] for q in fixes]
    assert 42.5740 < max(lats) < 42.5742 and 42.5644 < min(lats) < 42.5646
    k = 0.7365
    pts = [(q["lon"] * k * 111320, q["lat"] * 111320) for q in fixes]
    lap = sum(math_dist(a, b) for a, b in zip(pts, pts[1:]))
    assert 4800 < lap < 5000


def math_dist(a, b):
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def test_every_chain_track_declares_its_dressing_and_files_exist():
    for track in ("milford-road-course", "high-plains", "sand-creek"):
        d = ROOT / "tracks" / track
        cfg = json.loads((d / "track.config.json").read_text(encoding="utf-8"))
        ship = json.loads((d / "ship.json").read_text(encoding="utf-8"))
        b = cfg["scenery"]["bespoke"]
        assert "bespoke" in ship["steps"]["author"] and "house_seat" in ship["steps"]["gate"]
        assert ship["steps"]["ship"].index("grassfx_aerial") < ship["steps"]["ship"].index("track_folder")
        for group in b.get("blocks", []) + b.get("cards", []):
            if group.get("file"):
                assert (d / group["file"]).exists(), group["file"]
        assert (d / b["grassfx_zones"]["image"]).exists()
        assert cfg["lighting"]["grassfx"]["mask"] == "open", "a bright ground tile is past the default mask's ceiling"

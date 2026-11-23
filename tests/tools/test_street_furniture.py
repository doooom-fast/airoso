"""Ledger 0096 — Denver Grand Prix's street furniture (signals, two lamp classes, the MUTCD faces, the rail set):
the generators reproduce what is committed, the MUTCD limits the docstrings cite hold on the built parts, every lens
is its own named mesh, what AC refuses is refused here (L7), and the licence record covers every file.
Plain test_* functions, no bpy."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
FT = 0.3048


def _tool(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


mesh = _tool("street_furniture_mesh")
draw = _tool("street_furniture_draw")
sig = _tool("make_signals")
posts = _tool("make_streetlight_posts")
faces = _tool("make_sign_faces")
rail = _tool("make_rail_crossing")
MODELS, TEX = ROOT / "assets" / "models", ROOT / "assets" / "textures"


def _pot(n):
    return n > 0 and n & (n - 1) == 0


def _objects(name):
    return mesh.read_obj_objects((MODELS / name).read_text(encoding="utf-8"))


def _normal(o, face):
    return mesh._normal([o["verts"][i] for i in face[0]])


def test_generators_reproduce_the_committed_files():
    for gen in (sig, posts, rail):
        outs = gen.outputs()
        for name, text in outs.items():
            assert (MODELS / name).read_text(encoding="utf-8") == text, f"{name}: rerun tools/{gen.__name__}.py"
        assert gen.outputs() == outs                                 # deterministic
    text, face_png, blade_png = faces.outputs()
    for name, t in text.items():
        assert (MODELS / name).read_text(encoding="utf-8") == t, f"{name}: rerun tools/make_sign_faces.py"
    assert draw.write_or_check_png(TEX, sig.textures(), ["--check"], "signals") == 0
    assert draw.write_or_check_png(TEX, face_png, ["--check"], "sign-faces") == 0
    assert draw.write_or_check_png(faces.BLADES, blade_png, ["--check"], "sign-faces") == 0


def test_obj_objects_round_trip():
    m = sig.head("signal_head_5_dog_l")
    back = mesh.read_obj_objects(m.text())
    assert list(back) == [o.name for o in m.objects]
    for o in m.objects:
        assert back[o.name]["material"] == o.material
        assert sum(len(f[0]) - 2 for f in back[o.name]["faces"]) == o.tris()


def test_every_lens_is_its_own_mesh_facing_the_driver():
    spec = json.loads((MODELS / "signals.json").read_text(encoding="utf-8"))
    for name, h in spec["heads"].items():
        objs = _objects(h["file"])
        lenses = [n for n in objs if n.startswith("LENS_")]
        assert len(lenses) == len(sig.HEADS[name][1]) == len(h["lenses"])
        for rec in h["lenses"]:
            o = objs[rec["object"]]
            assert o["material"] == "SIGNALLENS_" + rec["aspect"] and rec["material"] in spec["bindings_proposed"]
            assert len(o["faces"]) == 1
            n = _normal(o, o["faces"][0])
            assert n[2] > 0 and abs(n[0]) < 1e-9 and abs(n[1]) < 1e-9
            xs = [v[0] for v in o["verts"]]
            assert abs((max(xs) - min(xs)) - 12 * 0.0254) < 1e-4          # MUTCD 4D.07: the 12 in lens
            assert all(-1e-6 <= u <= 1 + 1e-6 and -1e-6 <= v <= 1 + 1e-6 for u, v in o["faces"][0][1])
            assert max(v[2] for v in o["verts"]) > max(v[2] for v in objs["HOUSING"]["verts"] if abs(v[2] - sig.SEC_D) < 1e-9)
    # a left-turn arrow sits on the driver's left (-x) in the cluster head, a right-turn arrow on the right
    L = {r["aspect"]: r["centre_m"][0] for r in spec["heads"]["signal_head_5_dog_l"]["lenses"]}
    R = {r["aspect"]: r["centre_m"][0] for r in spec["heads"]["signal_head_5_dog_r"]["lenses"]}
    assert L["GA_L"] < 0 < L["G"] and R["G"] < 0 < R["GA_R"]
    ped = _objects("signal_ped_head.obj")["LENS_PED"]
    assert ped["material"] == "PEDLENS" and _normal(ped, ped["faces"][0])[2] > 0


def test_mutcd_mounting_limits_hold_for_every_arm_and_head():
    spec = json.loads((MODELS / "signals.json").read_text(encoding="utf-8"))
    for arm in spec["mast_arms"].values():
        xs = arm["default_head_stations_m"]
        assert xs and all(a - b >= 8 * FT - 1e-6 for a, b in zip(xs, xs[1:]))          # 4D.13: faces at least 8 ft apart
        assert max(xs) < arm["arm_length_m"] and min(xs) >= 3.0
        for (x, y, z), sx in zip(arm["head_origins_m"], xs):
            assert x == sx and abs(y - (spec["mast_arms"][next(iter(spec["mast_arms"]))]["arm_at_pole_m"][1] + x * spec["arm_rise_per_m"])) < 1e-3
            for h in spec["heads"].values():
                assert y - h["half_height_m"] >= 15 * FT, "4D.15: 15 ft under the housing"
                assert y + h["half_height_m"] <= 25.6 * FT, "4D.15: at most 25.6 ft to the top"
    at = spec["recipes"]["pedestal_head"]["at"]
    bottom = at[1] - spec["heads"]["signal_head_3"]["half_height_m"]
    assert 8 * FT <= bottom <= 19 * FT and abs(bottom + sig.BACKPLATE - spec["pedestal"]["top_m"]) < 1e-3
    assert 7 * FT <= spec["ped_head"]["mount_bottom_m"] <= 10 * FT                        # 4E.05
    assert abs(spec["pushbutton_post"]["button_height_m"] - 3.5 * FT) < 1e-3 and spec["pushbutton_post"]["button_height_m"] <= 4 * FT
    assert [a["arm_length_ft"] for a in spec["mast_arms"].values()] == [25, 35, 45]


def test_models_are_cheap_and_stand_on_the_datum():
    budget = {"signal_": 300, "streetlight_": 350, "sign_plate_": 40, "rail_": 60}
    for f in sorted(MODELS.glob("*.obj")):
        cap = next((c for p, c in budget.items() if f.name.startswith(p) and not f.name.startswith("streetlight_led")), None)
        if cap is None:
            continue
        objs = mesh.read_obj_objects(f.read_text(encoding="utf-8"))
        tris = sum(len(fc[0]) - 2 for o in objs.values() for fc in o["faces"])
        assert 0 < tris <= cap, (f.name, tris)
        assert all(o["material"] for o in objs.values()), f.name
    for name in ("signal_mast_arm_35.obj", "signal_pedestal.obj", "signal_pushbutton_post.obj", "streetlight_ped_acorn.obj",
                 "streetlight_arterial_twin.obj", "rail_crossbuck.obj"):
        ys = [v[1] for o in _objects(name).values() for v in o["verts"]]
        assert min(ys) <= -0.4, f"{name}: the foot runs on below the datum"


def test_lamp_classes_are_parametric_and_say_they_are_provisional():
    spec = json.loads((MODELS / "streetlight_posts.json").read_text(encoding="utf-8"))
    assert "PROVISIONAL" in spec["provisional"] and "led_cobra" in spec["already_owned"]
    assert set(spec["classes"]) == set(posts.CLASSES)
    for name, c in spec["classes"].items():
        objs = _objects(c["file"])
        assert objs["POST"]["material"] == "LIGHTPOST"
        lens = [n for n in objs if n.startswith("LENS")]
        assert lens == [r["object"] for r in c["lenses"]] and all(objs[n]["material"] == "LIGHTS" for n in lens)
    tw = spec["classes"]["arterial_twin"]
    assert len(tw["lenses"]) == 2 and tw["lenses"][0]["centre_m"][0] > 0 > tw["lenses"][1]["centre_m"][0]
    o = _objects(tw["file"])["LENS_1"]
    assert _normal(o, o["faces"][0])[1] < 0                              # the LED lens looks down
    # the parameters move the model: a 16 ft post is 4 ft taller than the committed 12 ft one
    m12, i12 = posts.pedestrian("x", 12.0, "globe")
    m16, i16 = posts.pedestrian("x", 16.0, "globe")
    assert abs((i16["top_of_fixture_m"] - i12["top_of_fixture_m"]) - 4 * FT) < 1e-3
    _, a = posts.arterial("x", 35.0, 12.0, 2.5, 1)
    assert abs(a["mounting_height_m"] - 37.5 * FT) < 1e-3 and abs(a["lenses"][0]["centre_m"][0] - 12 * FT) < 1e-3


def test_textures_are_power_of_two_with_the_edge_colour_bled():
    spec = json.loads((MODELS / "sign_faces.json").read_text(encoding="utf-8"))
    files = [TEX / f["file"] for f in spec["faces"].values()] + [faces.BLADES / f["file"] for f in spec["blades"]["streets"].values()]
    files += sorted(TEX.glob("signal_lens_*.png")) + sorted(TEX.glob("ped_signal_*.png"))
    assert len(files) == len(faces.FACES) + len(faces.DENVER_STREETS) + 20 + 3
    for f in files:
        w, h = Image.open(f).size
        assert _pot(w) and _pot(h) and max(w, h) <= 2048, f"{f.name}: {w}x{h}"
    stop = Image.open(TEX / "mutcd_r1-1.png")
    assert stop.mode == "RGBA" and stop.getpixel((0, 0))[3] == 0 and stop.getpixel((256, 256))[3] == 255
    assert min(stop.getpixel((0, 0))[:3]) > 200, "outside the octagon the colour is the white border's, not black"
    r, g, b, _ = stop.getpixel((256, 60))
    assert r > 150 and g < 80 and b < 80                                  # the red field above the legend
    ped = Image.open(TEX / "mutcd_w11-2.png")
    assert ped.getpixel((2, 2))[3] == 0 and ped.getpixel((256, 40))[3] == 255
    assert Image.open(TEX / "mutcd_r6-1l.png").size == (512, 128)
    lit, off = Image.open(TEX / "signal_lens_r.png").getpixel((64, 64)), Image.open(TEX / "signal_lens_r_off.png").getpixel((64, 64))
    assert lit[0] > 200 and off[0] < 80


def test_one_way_arrows_point_the_way_the_file_says():
    def bright_x(name):
        im = Image.open(TEX / name).convert("L")
        w, h = im.size
        col = [sum(im.getpixel((x, y)) for y in range(h)) for x in range(w)]
        return sum(x * c for x, c in enumerate(col)) / sum(col) / w
    # R6-1: the white arrow's shaft is full height only at the tail, so the arrow HEAD side is darker
    assert bright_x("mutcd_r6-1r.png") < 0.5 < bright_x("mutcd_r6-1l.png")
    a, b = Image.open(TEX / "mutcd_r3-5l.png"), Image.open(TEX / "mutcd_r3-5r.png")
    diff = ImageChops.difference(a.transpose(Image.FLIP_LEFT_RIGHT).crop((0, 0, 512, 300)), b.crop((0, 0, 512, 300)))
    assert max(ImageStat.Stat(diff).mean) < 0.5                         # R3-5R's arrow is R3-5L's, mirrored


def test_plate_uvs_are_the_documented_layout():
    spec = json.loads((MODELS / "sign_faces.json").read_text(encoding="utf-8"))
    rows = list(spec["faces"].values()) + list(spec["blades"]["streets"].values())
    assert {r["plate"] for r in rows} == {p + ".obj" for p in spec["plates"]}
    for r in rows:
        o = _objects(r["plate"])
        face, (w, h) = o["FACE"], r["size_m"]
        assert face["material"] == "SIGNFACE" and o["BACK"]["material"] == "SIGNBACK"
        assert _normal(face, face["faces"][0])[2] > 0 > _normal(o["BACK"], o["BACK"]["faces"][0])[2]
        xs, ys = [v[0] for v in face["verts"]], [v[1] for v in face["verts"]]
        assert abs((max(xs) - min(xs)) - w) < 2e-3 and abs((max(ys) - min(ys)) - h) < 2e-3, r["plate"]
        for i, (u, v) in zip(face["faces"][0][0], face["faces"][0][1]):
            x, y, _ = face["verts"][i]
            assert abs(u - (x / w + 0.5)) < 2e-3 and abs(v - (y / h + 0.5)) < 2e-3      # u left->right, v bottom->top
    assert spec["faces"]["r1-1"]["size_in"] == [30, 30] and spec["faces"]["r6-1l"]["size_in"] == [36, 12]
    assert spec["faces"]["r2-1_25"]["size_in"] == [24, 30] and spec["faces"]["w10-1"]["shape"] == "circle"
    assert abs(spec["faces"]["w11-2"]["size_in"][0] - 30 * 2 ** 0.5) < 1e-2


def test_the_faces_the_task_names_exist():
    need = ["r1-1", "r6-1l", "r6-1r", "r6-2l", "r6-2r", "r5-1", "r2-1_25", "r2-1_30", "r2-1_35", "r3-1", "r3-2", "r3-4", "r3-5l",
            "r3-5r", "r3-6l", "r3-7l", "r3-8_lt", "r15-1_railroad", "r15-1_crossing", "w10-1", "w11-2", "r3-11_bus"]
    assert not [c for c in need if c not in faces.FACES or not (TEX / f"mutcd_{c}.png").exists()]


def test_every_lap_street_has_a_blade():
    osm = ROOT / "tracks" / "denver-grand-prix" / "source" / "osm.json"
    lap = json.loads((ROOT / "tracks" / "denver-grand-prix" / "data" / "lap_ways.plan.json").read_text(encoding="utf-8"))
    ways = {w["id"]: w for w in json.loads(osm.read_text(encoding="utf-8"))["ways"]}
    names = {ways[i].get("tags", {}).get("name") for leg in lap["legs"] for i in leg["ways"]} - {None}
    assert names and names <= set(faces.DENVER_STREETS)
    assert all((faces.BLADES / faces.blade_file(s)).exists() for s in faces.DENVER_STREETS)
    assert faces.blade_legend("North Speer Boulevard") == ("N", "SPEER", "BLVD")
    assert faces.blade_legend("15th Street") == ("", "15TH", "ST")
    assert faces.blade_legend("West 14th Avenue Parkway") == ("W", "14TH AVE", "PKWY")
    assert faces.blade_legend("North Broadway") == ("N", "BROADWAY", "")
    assert faces.blade_legend("Saint Francis Way") == ("", "ST FRANCIS", "WAY")


def test_the_alphabet_covers_every_legend_and_fits():
    used = set("STOP ONE WAY DO NOT ENTER SPEED LIMIT ONLY LEFT RIGHT LANE MUST TURN BUS PUSH BUTTON FOR RAIL ROAD CROSSING 0123456789")
    for s in faces.DENVER_STREETS:
        used |= set("".join(faces.blade_legend(s)))
    assert used <= set(draw.GLYPHS)
    assert draw.text_width("STOP", 10) == 2 * draw.text_width("STOP", 5) and draw.text_width("II", 1) < draw.text_width("MM", 1)
    im = Image.new("RGB", (400, 100), (0, 0, 0))
    from PIL import ImageDraw
    sq = draw.draw_text(ImageDraw.Draw(im), "GALAPAGO BOULEVARD", 200, 30, 40, (255, 255, 255), max_w=300)
    assert sq < 1 and im.getbbox()[0] >= 48 and im.getbbox()[2] <= 352            # squeezed to the 300 px it was given


def test_the_crossbuck_is_two_48_by_9_blades_at_right_angles():
    o = _objects("rail_crossbuck.obj")
    import math
    dirs = []
    for word in ("RAILROAD", "CROSSING"):
        f = o[f"FACE_{word}"]
        v = [f["verts"][i] for i in f["faces"][0][0]]
        uv = f["faces"][0][1]
        a, b = v[uv.index((0.0, 0.0))], v[uv.index((1.0, 0.0))]
        assert abs(math.dist(a, b) - 48 * 0.0254) < 1e-4 and abs(math.dist(a, v[uv.index((0.0, 1.0))]) - 9 * 0.0254) < 1e-4
        dirs.append((b[0] - a[0], b[1] - a[1]))
        assert abs(sum(p[1] for p in v) / 4 - 9 * FT) < 1e-4
    assert abs(dirs[0][0] * dirs[1][0] + dirs[0][1] * dirs[1][1]) < 1e-6
    assert dirs[0][0] > 0 and dirs[0][1] < 0 and dirs[1][1] > 0                      # RAILROAD reads down to the right, CROSSING up
    assert max(v[2] for v in o["FACE_CROSSING"]["verts"]) > max(v[2] for v in o["FACE_RAILROAD"]["verts"])


def test_the_licence_record_covers_every_generated_file():
    lic = json.loads((ROOT / "assets" / "licenses.json").read_text(encoding="utf-8"))
    rows = [e for e in lic["bundled_assets"] if "ledger 0096" in e["name"]]
    listed = {f for e in rows for f in e["files"]}
    assert rows and all(e["license"] == "CC0-1.0" for e in rows)
    want = {f"models/{n}" for g in (sig, posts, rail) for n in g.outputs()} | {f"models/{n}" for n in faces.outputs()[0]}
    want |= {f.name for f in TEX.glob("signal_lens_*.png")} | {f.name for f in TEX.glob("ped_signal_*.png")}
    want |= {f"mutcd_{c}.png" for c in faces.FACES}
    assert want <= listed, sorted(want - listed)
    assert all((ROOT / "assets" / ("" if f.startswith("models/") else "textures/") / f).exists() for f in listed), "a listed file is missing"

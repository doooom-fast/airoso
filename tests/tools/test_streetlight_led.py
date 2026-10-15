"""Ledger 0056 — the modern LED street light: generator determinism and dimensions, normals, the render-point
budget, the one-light-per-lens clustering, verify_race's mast footprint, and the recorded lens offset."""
from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def _tool(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


gen = _tool("make_streetlight_led")
pool = _tool("streetlight_pool")


def _parse(text):
    v, faces, g = [], [], 0
    for ln in text.splitlines():
        p = ln.split()
        if not p:
            continue
        if p[0] == "v":
            v.append(tuple(map(float, p[1:4])))
        elif p[0] == "s":
            g = 0 if p[1] == "off" else int(p[1])
        elif p[0] == "f":
            faces.append(([int(q.split("/")[0]) - 1 for q in p[1:]], g))
    return v, faces


def test_committed_model_files_are_the_generators_output():
    outs = gen.outputs()
    for name, text in outs.items():
        assert (gen.OUT / name).read_text(encoding="utf-8") == text, f"{name}: rerun tools/make_streetlight_led.py"
    assert gen.outputs() == outs                                   # deterministic


def test_dimensions_are_the_caltrans_es6a_type21_light():
    s = json.loads((gen.OUT / "streetlight_led.json").read_text(encoding="utf-8"))
    assert abs(s["pole_height_m"] - 35 * 0.3048) < 1e-3
    assert abs(s["arm_length_m"] - 12 * 0.3048) < 1e-3
    assert 11.0 <= s["mounting_height_m"] <= 12.0 and abs(s["mounting_height_m"] - (38 + 9 / 12) * 0.3048) < 1e-3
    lx, ly, lz = s["lens_centre_m"]
    assert lx > s["arm_length_m"] and ly == s["mounting_height_m"] and lz == 0.0
    v, _ = _parse((gen.OUT / s["files"]["post_twin"]).read_text(encoding="utf-8"))
    head = [p for p in v if p[0] > 3.4]
    assert min(p[1] for p in head) > ly, "the housing must stand above the lens face (no z-fight, lens visible)"
    assert max(p[1] for p in v) < ly + 0.25                       # photocell top: nothing pokes far above the head
    assert min(p[1] for p in v) == -s["pole_bury_m"]
    assert 0.10 < s["mast_radius_m"] < 0.15


def _corner_normals_budget(text):
    """render points if every smooth group shares its vertices and every flat face owns its own (tangents ignored)"""
    v, faces = _parse(text)
    keys = set()
    for fi, (ix, g) in enumerate(faces):
        for i in ix:
            keys.add((i, g) if g else (i, "f", fi))
    return len(keys)


def test_render_point_budget_is_a_tenth_of_the_2026_10_lamp():
    twin = _corner_normals_budget((gen.OUT / "streetlight_led_post_twin.obj").read_text(encoding="utf-8"))
    single = _corner_normals_budget((gen.OUT / "streetlight_led_post_single.obj").read_text(encoding="utf-8"))
    lens = _corner_normals_budget((gen.OUT / "streetlight_led_lens.obj").read_text(encoding="utf-8"))
    # measured through the prep + AC exporter in Blender 4.2 (tangent splits on top): twin ~360, single ~204, lens 4-5
    assert twin + lens <= 300 and single + lens <= 170, (twin, single, lens)
    assert lens == 4


def test_faces_point_outward_and_the_lens_faces_down():
    v, faces = _parse((gen.OUT / "streetlight_led_post_twin.obj").read_text(encoding="utf-8"))
    for ix, g in faces:
        c = [sum(v[i][k] for i in ix) / len(ix) for k in range(3)]
        n = gen._normal([v[i] for i in ix])
        if g == 1:                                                  # pole wall: away from the axis
            assert n[0] * c[0] + n[2] * c[2] > 0
    lv, lf = _parse((gen.OUT / "streetlight_led_lens.obj").read_text(encoding="utf-8"))
    n = gen._normal([lv[i] for i in lf[0][0]])
    assert n[1] < 0 and abs(n[0]) < 1e-9 and abs(n[2]) < 1e-9


def test_one_light_per_lens_even_across_a_bucket_edge():
    from scripts.ac.ext_config import lamp_clusters
    lens = lambda cx, cz: [(cx - 0.26, 11.8, cz - 0.11), (cx + 0.26, 11.8, cz - 0.11), (cx + 0.26, 11.8, cz + 0.11),
                           (cx - 0.26, 11.8, cz + 0.11)]
    pts = lens(5.0, 20.0) + lens(60.0, 20.0)                       # the first straddles x = 5 (the old bucket edge)
    pts.append(pts[0])                                             # an exporter-duplicated corner
    heads = sorted(lamp_clusters(pts))
    assert len(heads) == 2
    assert all(abs(a - b) < 1e-9 for a, b in zip(heads[0], (5.0, 11.8, 20.0)))   # duplicates never bias the centroid
    marker = [(9.99, 7.0, 3.0), (10.01, 7.0, 3.0), (9.99, 7.02, 3.0)]  # a 2026-10 marker on the bucket edge
    assert len(lamp_clusters(marker)) == 1


def test_verify_race_reads_the_selected_models_mast():
    vr = _tool("verify_race")
    led = vr.lamp_model_info({"scenery": {"streetlights": {"model": "led_cobra"}}})
    assert led["model"] == "led_cobra" and 0.10 < led["mast_r_m"] < 0.15 and abs(led["post_h_m"] - 10.668) < 1e-3
    assert vr.lamp_model_info({}) == {"model": "street_lamp_2026_10", "post_h_m": None, "mast_r_m": None}
    assert vr._author_lamps_constant("HEAD_ABOVE_ROAD_M", -1.0) == 8.944


def test_the_lens_moves_by_one_constant_offset_per_lamp():
    cl = [(float(i), 0.0, 0.0) for i in range(-200, 201)]           # a straight road along +x at y = 0
    heads = [(0.0, 8.944, 10.0), (55.0, 9.444, -12.0)]              # one each side, the second 0.5 m higher
    old, new = pool.predicted_lights(heads, cl)
    offs = []
    for (hx, hy, hz), o, n in zip(heads, old, new):
        rz = -1.0 if hz > 0 else 1.0                                # road-ward
        offs.append((round((n[2] - o[2]) * rz, 4), round(n[1] - o[1], 4), round(n[0] - o[0], 4)))
    assert offs[0] == offs[1], offs
    road_ward, up, along = offs[0]
    assert along == 0.0 and abs(road_ward - 2.440) < 5e-3 and abs(up - 4.718) < 5e-3
    assert abs(old[0][1] - 6.943) < 5e-3                            # ledger 0043: the 2026-10 light 6.94 m over the road
    assert abs(new[0][1] - (11.811 - 0.15)) < 1e-6                  # the light 0.15 m under an 11.81 m lens


def test_csp_pool_model_shapes():
    sl = {"intensity": 0.013, "range_m": 25.0, "spot_deg": 150, "spot_sharpness": 0.2, "range_gradient_offset": 0.5,
          "diffuse_concentration": 0.25}
    L = pool.Light(sl)
    assert abs(L.E((0, 6.9, 0), (0, 0, 0)) - 0.013) < 1e-9         # plateau + spot core straight down
    assert L.E((0, 6.9, 0), (24.5, 0, 0)) == 0.0                    # past the range sphere
    assert L.E((0, 11.6, 0), (10, 0, 0)) > L.E((0, 6.9, 0), (10, 0, 0))   # the taller light reaches the flank harder
    assert math.isclose(L.E((0, 11.6, 0), (0, 0, 0)), 0.013)

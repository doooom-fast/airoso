"""tools/plan_buildings.py: the shadow stage on a drawn photograph (a box of known height, a sun of known elevation), the class
rules, and the fall-backs. Pillow only, no bpy."""
from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

spec = importlib.util.spec_from_file_location("plan_buildings", ROOT / "tools" / "plan_buildings.py")
pb = importlib.util.module_from_spec(spec)
sys.modules["plan_buildings"] = pb
spec.loader.exec_module(pb)


class _Photo:
    """a drawn aerial: one tile = 0.5 m"""

    def __init__(self, img):
        self.img, self.px = img, img.load()
        self.w, self.h = img.size
        self.m_per_px = 0.5

    def bright(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            r, g, b = self.px[int(x), int(y)]
            return (r + g + b) / 3.0
        return None


def _scene(height_m, sun_el_deg, shadow_az_deg, ground=(150, 140, 110)):
    """a 30 x 16 m box at the middle, its shadow drawn as the box swept along the shadow direction by height / tan(el)"""
    img = Image.new("RGB", (400, 400), ground)
    d = ImageDraw.Draw(img)
    box = [(170, 184), (230, 184), (230, 216), (170, 216)]          # 30 x 16 m
    L = height_m / math.tan(math.radians(sun_el_deg)) / 0.5          # px
    th = math.radians(shadow_az_deg)
    ux, uy = math.sin(th), -math.cos(th)
    for k in range(int(L) + 1):
        d.polygon([(x + ux * k, y + uy * k) for x, y in box], fill=(60, 56, 46))
    d.polygon(box, fill=(210, 205, 195))
    return img, box


def test_shadow_direction_and_length_recover_a_drawn_box():
    img, box = _scene(6.0, 40.0, 300.0)
    photo = _Photo(img)
    az, votes = pb.shadow_direction(photo, [box])
    assert votes == 1 and abs((az - 300.0 + 180) % 360 - 180) < 12, az
    th = math.radians(az)
    L, why = pb.shadow_length_m(photo, box, pb.PolyIndex([box]), math.sin(th), -math.cos(th), 60.0)
    assert L is not None, why
    assert abs(L * math.tan(math.radians(40.0)) - 6.0) < 0.6, (L, why)


def test_a_dark_reference_is_not_a_measurement():
    img, box = _scene(6.0, 40.0, 300.0, ground=(40, 42, 38))
    photo = _Photo(img)
    L, why = pb.shadow_length_m(photo, box, pb.PolyIndex([box]), math.sin(math.radians(300)), -math.cos(math.radians(300)), 60.0)
    assert L is None and "dark reference" in why


def test_a_run_into_another_footprint_is_blocked_not_measured():
    img, box = _scene(12.0, 40.0, 270.0)
    other = [(120, 170), (160, 170), (160, 230), (120, 230)]       # just west, inside the shadow
    photo = _Photo(img)
    L, why = pb.shadow_length_m(photo, box, pb.PolyIndex([box, other]), -1.0, 0.0, 60.0)
    assert L is None and "blocked" in why


def test_sun_from_shadow_puts_a_morning_sun_opposite_the_shadows():
    best = pb.sun_from_shadow(36.28, -115.02, "2013-09-28", "-07:00", 302.0)
    assert best is not None and best[0] < 2.0
    hh = int(best[1][11:13])
    assert 9 <= hh <= 10 and 28 < best[3] < 40, best   # the reading tools/author_bespoke_blend.py's Nevada tents were measured at


def test_classes_from_tags_then_area():
    plan = {"yes_by_area": [[60, "shed"], [350, "house"], [1500, "commercial"], [1e9, "industrial"]]}
    assert pb.classify({"tag": "warehouse", "area": 100}, plan)[0] == "industrial"
    assert pb.classify({"tag": "roof", "area": 100}, plan)[0] == "canopy"
    assert pb.classify({"tag": "yes", "area": 200}, plan)[0] == "house"
    assert pb.classify({"tag": None, "area": 2000}, plan)[0] == "industrial"
    for cls in ("house", "apartments", "commercial", "industrial", "shed"):
        assert cls in pb.STOREY_M and cls in pb.DEFAULT_WALL_M and cls in pb.FORM


def test_a_later_source_on_an_earlier_footprint_is_dropped_and_offers_its_height():
    sq = lambda x, y, s: [[x, y], [x + s, y], [x + s, y + s], [x, y + s]]
    recs = [
        {"key": "osm1", "tag": "house", "levels": None, "height": None, "src": "OSM", "ring": sq(-117.0, 32.8, 0.0002)},
        {"key": "osm2", "tag": "house", "levels": "2", "height": None, "src": "OSM", "ring": sq(-117.0, 32.801, 0.0002)},
        {"key": "ms1", "tag": "yes", "levels": None, "height": 5.1, "src": "Microsoft tile", "ring": sq(-116.99995, 32.80005, 0.0001)},  # inside osm1
        {"key": "ms2", "tag": "yes", "levels": None, "height": 7.0, "src": "Microsoft tile", "ring": sq(-116.99995, 32.80105, 0.0001)},  # inside osm2
        {"key": "ms3", "tag": "yes", "levels": None, "height": 4.0, "src": "Microsoft tile", "ring": sq(-117.002, 32.8, 0.0002)},        # on its own
    ]
    kept = pb.dedupe(recs)
    assert [r["key"] for r in kept] == ["osm1", "osm2", "ms3"]
    assert kept[0]["alt_height"] == 5.1 and kept[0]["alt_src"] == "Microsoft tile"
    assert "alt_height" not in kept[1]                    # it has levels of its own: nothing offered
    assert pb.height_label("OSM") == "OSM height" and pb.height_label("Microsoft tile").startswith("Microsoft height")


def test_an_untagged_footprint_with_a_low_known_height_is_a_house_not_a_commercial_block():
    plan = {"yes_by_area": [[60, "shed"], [350, "house"], [1500, "commercial"], [1e9, "industrial"]]}
    assert pb.classify({"tag": "yes", "area": 500, "height": 4.8}, plan)[0] == "house"
    assert pb.classify({"tag": "yes", "area": 500, "alt_height": 4.8}, plan)[0] == "house"
    assert pb.classify({"tag": "yes", "area": 500, "height": 12.0}, plan)[0] == "commercial"
    assert pb.classify({"tag": "yes", "area": 500}, plan)[0] == "commercial"
    assert pb.classify({"tag": "yes", "area": 40, "height": 3.0}, plan)[0] == "shed"
    assert pb.classify({"tag": "yes", "area": 1200, "height": 4.0}, plan)[0] == "commercial"


def test_every_planned_track_file_names_a_source_per_height():
    for track in ("high-plains", "sand-creek", "exotics-racing-lv", "san-diego-lake-murray"):
        f = ROOT / "tracks" / track / "source" / "bespoke" / "buildings.json"
        if not f.exists():
            continue
        rows = json.loads(f.read_text(encoding="utf-8"))
        assert rows
        for r in rows:
            assert r["_h"] and r["_class"] and r["form"] in ("hip", "gable", "flat", "flat_parapet")
            assert any(w in r["_h"] for w in ("OSM", "shadow", "[invented]", "Microsoft height", "height from")), r["_h"]
            if r["form"] in ("hip", "gable"):
                assert r["ridge_h_m"] > r["wall_h_m"] >= pb.MIN_WALL_M.get(r["class"], 2.6)

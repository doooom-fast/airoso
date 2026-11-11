"""Milford furniture pass 3 (ledger 0082, 0.1.8): the site buildings and F1's north-east end off the 2017 lidar already on
disk, declared through existing keys only (a blocks group's "file", the screen kind), and the built-ground seat report.

stdlib + numpy (seat_built's reader).
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MF = ROOT / "tracks" / "milford-road-course-lm"
P3 = MF / "source" / "furniture" / "pass3"


def test_blocks_are_the_measured_roofs():
    tiers = {(t["src"], t["tier"], t["area_m2"]): t for t in json.loads((P3 / "tiers.json").read_text())}
    blocks = json.loads((P3 / "blocks.json").read_text())
    assert [b["key"] for b in blocks] == ["mpg_west_bldg_a", "mpg_west_bldg_b", "mpg_west_bldg_c", "mpg_nw_small"]
    by_h = {round(t["h50"], 2): t for t in tiers.values()}
    for b in blocks:
        t = by_h[b["wall_h_m"]]
        assert b["footprint_lonlat"] == t["footprint_lonlat"], b["key"]
        assert b["off_terrain"] is True and b["form"] == "flat"
        assert b["roof_z_m"] == t["roof_z_local_m"]                       # the roof at its measured elevation
        assert "[measured]" in b["_source"] and "NAIP 2022 shows it standing" in b["_source"]
        assert "[invented: no wall is seen from above]" in b["_source"]   # the skin is the one guess, and says so


def test_config_names_the_file_once_and_plant_a_is_measured():
    cfg = json.loads((MF / "track.config.json").read_text(encoding="utf-8"))
    groups = cfg["scenery"]["bespoke"]["blocks"]
    assert sum(g.get("file") == "source/furniture/pass3/blocks.json" for g in groups) == 1
    plant = next(g for g in groups if g.get("key") == "mpg_plant_a")
    pa = next(t for t in json.loads((P3 / "tiers.json").read_text()) if t["src"] == 104)
    assert plant["wall_h_m"] == round(pa["h50"], 1) and "[measured" in plant["_source"]
    ship = json.loads((MF / "ship.json").read_text(encoding="utf-8"))
    assert "source/furniture/pass3/blocks.json" in ship["sync_in"]["required"]


def test_no_other_track_names_pass3():
    """the pass's files and its two opt-in keys (a far block's roof_z_m, scenery.bespoke.reseat_on_prep) are Milford's alone"""
    for cfgp in sorted((ROOT / "tracks").glob("*/track.config.json")):
        txt = cfgp.read_text(encoding="utf-8")
        if cfgp.parent.name == "milford-road-course-lm":
            assert json.loads(txt)["scenery"]["bespoke"]["reseat_on_prep"] is True
            continue
        # High Plains 0.1.7 (ledger 0084, runbook 0084-2 step 3) re-seats its pit-wall K-rail with reseat_on_prep too
        keys = ("source/furniture/pass3", "roof_z_m") + (() if cfgp.parent.name == "high-plains-lm" else ("reseat_on_prep",))
        for key in keys:
            assert key not in txt, (cfgp, key)
    for f in (ROOT / "tracks").glob("*/source/bespoke/*.json"):
        if f.parts[-4] == "pikes-peak-lm":     # Pikes Peak 0.2.1 (ledger 0085): its lidar blocks stand at their measured roofs
            continue
        assert "roof_z_m" not in f.read_text(encoding="utf-8"), f


def test_reseat_runs_only_when_the_key_says_so():
    sh = (ROOT / "tools" / "ship_track.sh").read_text(encoding="utf-8")
    i = sh.index("reseat_bespoke_blend.py")
    block = sh[sh.rindex("rm -f \"$PROJ/data/reseat_bespoke.json\"", 0, i):i]
    assert "get('reseat_on_prep') is True" in block and '= "True" ]; then' in block
    assert "reseat" not in (ROOT / "tools" / "ship_sd.sh").read_text(encoding="utf-8")   # Lake Murray's chain of record
    src = (ROOT / "tools" / "reseat_bespoke_blend.py").read_text(encoding="utf-8")
    assert 'spec.get("reseat_on_prep") is not True' in src


def test_f1_ne_end_joins_the_built_piece_and_is_measured():
    cfg = json.loads((MF / "track.config.json").read_text(encoding="utf-8"))
    rails = {r["key"]: r for r in cfg["scenery"]["bespoke"]["rails"]}
    ne, end = rails["f1_nw_screen_ne"], rails["f1_nw_screen_ne_end"]
    assert end["polyline_lonlat"][0] == ne["polyline_lonlat"][0]       # it starts where the built NE piece ends
    assert end == json.loads((P3 / "f1_ne_end.json").read_text())
    bins = [b for b in json.loads((P3 / "f1ne_bins.json").read_text()) if "top90" in b]
    assert 3.9 < end["height_m"] < 4.4 and "[measured]" in end["_source"] and len(bins) >= 12


def _seat():
    spec = importlib.util.spec_from_file_location("seat_built_mf", P3 / "scripts" / "seat_built.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_seat_built_reads_the_highest_ground_under_a_point():
    import numpy as np
    m = _seat()
    V = np.array([[0, 0, 0], [10, 0, 0], [0, 0, 10], [0, 1.0, 0], [10, 1.0, 0], [0, 1.0, 10]], float)
    G = m.Ground(V, np.array([[0, 1, 2], [3, 4, 5]]))
    assert abs(G.height(2.0, 2.0) - 1.0) < 1e-9          # two layers: the higher is the ground a thing stands on
    assert G.height(20.0, 20.0) is None


def test_seat_built_flags_a_buried_rail():
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        _buried_rail(Path(d))


def _buried_rail(tmp_path):
    obj = tmp_path / "data"
    obj.mkdir()
    (obj / "track.obj").write_text(
        "o 1GRASS_0\nv 0 0 0\nv 20 0 0\nv 0 0 20\nv 20 0 20\nf 1 2 3\nf 2 4 3\n"
        "o GUARDRAIL_W_0\nv 5 0.45 5\nv 5 -0.2 5\nv 6 0.45 5\nv 6 -0.2 5\nf 5 6 8 7\n", encoding="utf-8")
    origin = {"lon": -83.66, "lat": 42.57}
    (tmp_path / "data" / "centerline.local.json").write_text(json.dumps({"origin": origin}))
    lon = lambda e: origin["lon"] + e / 82107.2   # noqa: E731
    lat = lambda n: origin["lat"] + n / 111084.4   # noqa: E731
    (tmp_path / "track.config.json").write_text(json.dumps({"scenery": {"bespoke": {"rails": [
        {"key": "g", "kind": "wbeam", "height_m": 0.7, "polyline_lonlat": [[lon(4), lat(5)], [lon(7), lat(5)]]}]}}}))
    import subprocess
    import sys
    r = subprocess.run([sys.executable, str(P3 / "scripts" / "seat_built.py"), str(tmp_path)], capture_output=True, text=True)
    assert r.returncode == 1 and "FAIL" in r.stdout, r.stdout   # 0.45 m showing of a 0.70 m rail: buried

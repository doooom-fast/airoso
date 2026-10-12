"""Ledger 0046 E3 — the far ring (GRASS_FAR*) is VISUAL ONLY and every engine path a non-tiered track runs is
unchanged: no digit prefix, so no gate lens, physics bucket or drivable list takes it; ext_config never lists it for
GrassFX or occlusion (the v0.12.1-0.12.6 TDR whole-PC freeze came from enrolling a far backdrop); pbr binds it a
TEXTURED dry-chaparral row (never the texture-less MOUNTAINS slot that renders black, L7) and the new row changes no
existing name's binding; verify_kn5 holds it to the vertex cap and refuses a digit-prefixed far mesh; the heightfield
margin and the sampler are no-ops for a track that does not declare them."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.ac import ext_config, pbr, verify_kn5  # noqa: E402
from scripts.ac import kn5_ground_check  # noqa: E402
from scripts.geometry import drive_test  # noqa: E402

FAR = ["GRASS_FAR", "GRASS_FAR_0", "GRASS_FAR_7"]


def test_no_gate_or_physics_lens_takes_the_far_ring():
    lenses = [("drive_test.DRIVABLE", drive_test.DRIVABLE), ("drive_test.SOFT", drive_test.SOFT),
              ("verify_kn5.DRIVABLE", verify_kn5.DRIVABLE), ("kn5_ground_check.BUCKETS", kn5_ground_check.BUCKETS),
              ("audit_mesh groups", ("1ROAD_MAIN", "1ROAD", "1GRASS", "HWYSTRUCT", "1WALL", "1KERB"))]
    for name in FAR:
        assert not name[0].isdigit(), "no physical digit prefix: AC never collides with it"
        for lens, prefixes in lenses:
            assert not name.upper().startswith(tuple(prefixes)), (name, lens)
    # the audit's group reader and the kn5 ground check key on the same prefixes in the code itself
    src = (ROOT / "scripts" / "geometry" / "audit_mesh.py").read_text(encoding="utf-8")
    assert '("1ROAD_MAIN", "1ROAD", "1GRASS", "HWYSTRUCT", "1WALL", "1KERB")' in src


def _ext(groups):
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    (d / "track.config.json").write_text(json.dumps({"slug": "t", "lighting": {"grassfx": True}}))
    (d / "data" / "track.obj").write_text("".join(f"o {g}\n" for g in groups))
    return ext_config.generate(d).read_text(encoding="utf-8")


def test_grassfx_and_occluders_never_list_the_far_ring():
    ini = _ext(["1ROAD_road", "1KERB_sidewalk", "1GRASS_0", "1GRASS_1", "1GRASS_2", "GRASS_FAR_0", "GRASS_FAR_1", "HOUSE"])
    for ln in ini.splitlines():
        if ln.startswith(("GRASS_MESHES", "OCCLUDING_MESHES", "MESHES")):
            assert "GRASS_FAR" not in ln, ln
    grass = [ln for ln in ini.splitlines() if ln.startswith("GRASS_MESHES")]
    assert grass and all(t in grass[0] for t in ("1GRASS_0", "1GRASS_1", "1GRASS_2")), grass


def test_pbr_far_row_is_textured_and_shadows_nothing():
    r = pbr.resolve("GRASS_FAR_3")
    assert r["key"] == "GRASS_FAR" and r["diffuse"] is not None and r["diffuse"].name == "ground_dry_diffuse.jpg"
    assert pbr.TEXTURES["MOUNTAINS"][0] is None, "the slot the far ring must never use (renders black)"
    assert "GRASS_FAR" in pbr.KS_PROPS
    # a track's 1GRASS override (Lake Murray's green turf) does not reach the far ring: overrides bind by key
    assert pbr.resolve("GRASS_FAR_0", overrides={"1GRASS": {"diffuse": "turf.jpg"}})["overridden"] is False
    # the new row changes no other binding: every existing key (and a split tile of it) matches as without it
    without = [k for k in pbr.TEXTURES if k != "GRASS_FAR"]
    for k in without:
        for name in (k, k + "_0", k.lower() + "_mat"):
            old = next((x for x in without if name.upper().startswith(x)), None)
            assert pbr.match_key(name) == old, name


def test_verify_kn5_holds_the_far_ring_to_the_cap_and_off_physics():
    ok = [{"name": "GRASS_FAR_0", "nverts": 59000}, {"name": "1GRASS_0", "nverts": 60000}]
    assert verify_kn5.far_ring_checks(ok) == []
    bad = verify_kn5.far_ring_checks([{"name": "GRASS_FAR_1", "nverts": 70000}, {"name": "1GRASS_FAR", "nverts": 10}])
    assert any("OVER-CAP far ring" in f for f in bad) and any("digit prefix" in f for f in bad)
    assert verify_kn5.far_ring_checks([{"name": "1GRASS_0", "nverts": 1}]) == []      # no far ring: silent


def test_untiered_tracks_are_untouched():
    from scripts.elevation import heightfield, terrain_sample
    assert heightfield.hf_margin_m({}) == heightfield.HF_MARGIN_M == 150.0
    assert heightfield.hf_margin_m({"terrain": {"terrain_band_m": 22.0}}) == 150.0
    assert heightfield.hf_margin_m({"terrain": {"margin_m": 600}}) == 600.0
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    (d / "track.config.json").write_text(json.dumps({"slug": "t", "terrain": {"terrain_band_m": 22.0}}))
    pts = [[float(x), 0.0, 0.0] for x in range(0, 100, 5)]
    (d / "data" / "centerline.local.json").write_text(json.dumps(
        {"points_xyz_m": pts, "widths_m": [10.0] * len(pts), "origin": {"lon": -117.0, "lat": 32.8, "elev_m": 100.0}}))
    before = sorted(p.name for p in (d / "data").iterdir())
    assert terrain_sample.run(d) is None
    assert sorted(p.name for p in (d / "data").iterdir()) == before, "an untiered track gets no terrain files"


def test_lake_murray_far_ring_wears_its_chaparral_and_the_chain_carries_it():
    """ledger 0046 fix round (visual verify): the stock far row is a neutral grey gravel; Lake Murray binds its own
    grey-olive chaparral through texture_overrides (project-relative), and both ship chains carry the file in"""
    sd = ROOT / "tracks" / "san-diego-lake-murray"
    cfg = json.loads((sd / "track.config.json").read_text(encoding="utf-8"))
    rel = cfg["texture_overrides"]["GRASS_FAR"]["diffuse"]
    assert rel == "textures/chaparral_far_diffuse.jpg" and (sd / rel).is_file()
    with tempfile.TemporaryDirectory() as d:
        proj = Path(d)
        (proj / "track.config.json").write_text(json.dumps(cfg), encoding="utf-8")
        (proj / "textures").mkdir()
        (proj / rel).write_bytes((sd / rel).read_bytes())
        ov = pbr.load_overrides(proj)
        assert Path(ov["GRASS_FAR"]["diffuse"]) == proj / rel
        r = pbr.resolve("GRASS_FAR_1", overrides=ov)
        assert r["key"] == "GRASS_FAR" and r["overridden"] is True
        # 1GRASS keeps its own turf: the two keys never cross
        assert Path(ov["1GRASS"]["diffuse"]).name == "grass_diffuse.jpg"
    ship_sd = (ROOT / "tools" / "ship_sd.sh").read_text(encoding="utf-8")
    assert 'TRACK_TEXTURES="textures/chaparral_far_diffuse.jpg"' in ship_sd
    spec = json.loads((sd / "ship.json").read_text(encoding="utf-8"))
    assert rel in spec["sync_in"]["optional"]

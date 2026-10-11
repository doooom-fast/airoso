"""tools/pack_release.py — the CC0 package's race layouts. By default it is the Street Loop only (strip_race_layouts:
san_diego_lake_murray_race.kn5, every san_diego_lake_murray_closure_<id>.kn5 (ledger 0049) and the two race layouts
leave it); --with-race keeps them. The split is a tool, not a licence verdict: which package goes public is
Kevin's call at publish time (Kevin 2026-10-11). The release texts carry [[street-only]] / [[with-race]]
alternatives that render_variant resolves per package."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import pack_release as pr  # noqa: E402

SLUG = pr.SLUG


def _folder(layouts):
    d = Path(tempfile.mkdtemp())
    f = d / SLUG
    f.mkdir()
    (f / f"{SLUG}.kn5").write_bytes(b"road")
    (f / f"{SLUG}_race.kn5").write_bytes(b"race")
    for lo in layouts:
        lid = lo["id"]
        (f / f"models_{lid}.ini").write_text("[MODEL_0]\n")
        (f / "ui" / lid).mkdir(parents=True)
        (f / "ui" / lid / "ui_track.json").write_text("{}")
        (f / lid / "data").mkdir(parents=True)
        (f / lid / "map.png").write_bytes(b"png")
        (f / f"{SLUG}__{lid}.kn5").write_bytes(b"spawn")
    cfg = d / "track.config.json"
    cfg.write_text(json.dumps({"slug": SLUG, "layouts": layouts}))
    return f, cfg


THREE = [{"id": "street", "kind": "street", "race_furniture": False},
         {"id": "race_cw", "kind": "race", "race_furniture": True},
         {"id": "race_acw", "kind": "race", "race_furniture": True}]


def test_race_layouts_and_race_kn5_leave_the_cc0_folder_street_stays():
    f, cfg = _folder(THREE)
    removed = set(pr.strip_race_layouts(f, cfg))
    assert removed == {f"{SLUG}_race.kn5",
                       "models_race_cw.ini", "ui/race_cw", "race_cw", f"{SLUG}__race_cw.kn5",
                       "models_race_acw.ini", "ui/race_acw", "race_acw", f"{SLUG}__race_acw.kn5"}, removed
    assert (f / "models_street.ini").exists() and (f / "ui" / "street" / "ui_track.json").exists()
    assert (f / "street" / "map.png").exists() and (f / f"{SLUG}__street.kn5").exists() and (f / f"{SLUG}.kn5").exists()
    assert not (f / f"{SLUG}_race.kn5").exists() and not (f / "ui" / "race_cw").exists()


def test_single_street_layout_folder_is_untouched_except_a_stray_race_kn5():
    f, cfg = _folder([{"id": "street", "kind": "street", "race_furniture": False}])
    removed = pr.strip_race_layouts(f, cfg)
    assert removed == [f"{SLUG}_race.kn5"], removed


def test_refuses_to_leave_no_layout():
    f, cfg = _folder([{"id": "race_cw", "kind": "race", "race_furniture": True}])
    try:
        pr.strip_race_layouts(f, cfg)
    except SystemExit as e:
        assert "no layout" in str(e)
    else:
        raise AssertionError("a race-only folder was stripped to nothing")


# --- previews: every layout's ui/<id>/preview.svg becomes preview.png (multi-layout folders have no root one)
_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" width="64" height="36"><rect width="64" height="36" fill="#102030"/>'
        '<polyline points="2,2 30,20 60,5" stroke="#ff2010" stroke-width="3" fill="none"/></svg>')


def test_multi_layout_previews_are_rasterised_per_layout():
    from PIL import Image
    f, _ = _folder(THREE)
    ui = f / "ui"
    for lo in THREE:
        (ui / lo["id"] / "preview.svg").write_text(_SVG, encoding="utf-8")
    done = pr.rasterize_previews(ui)
    assert sorted(done) == ["race_acw", "race_cw", "street"], done
    for lo in THREE:
        d = ui / lo["id"]
        assert not (d / "preview.svg").exists() and (d / "preview.png").exists(), d
        im = Image.open(d / "preview.png").convert("RGB")
        assert im.size == (64, 36) and im.getpixel((0, 35)) == (0x10, 0x20, 0x30)
    assert not (ui / "preview.png").exists(), "no root preview invented for a multi-layout folder"


def test_root_preview_still_rasterised_and_a_real_png_is_never_overwritten():
    from PIL import Image
    f, _ = _folder([{"id": "street", "kind": "street", "race_furniture": False}])
    ui = f / "ui"
    (ui / "preview.svg").write_text(_SVG, encoding="utf-8")                 # single-layout: the root ui/
    real = Image.new("RGB", (8, 8), (1, 2, 3))
    real.save(ui / "street" / "preview.png")                                 # the engine's real OSM preview ...
    (ui / "street" / "preview.svg").write_text(_SVG, encoding="utf-8")      # ... beside a stale fallback SVG
    done = pr.rasterize_previews(ui)
    assert sorted(done) == [".", "street"], done
    assert (ui / "preview.png").exists() and not (ui / "preview.svg").exists()
    assert Image.open(ui / "street" / "preview.png").size == (8, 8), "the real preview was overwritten"
    assert not (ui / "street" / "preview.svg").exists()


def test_full_release_texts_credit_the_k_rail_on_every_race_kn5():
    texts = pr.TRACK_DIR / "release"
    kn5s = (f"{SLUG}_race.kn5", f"{SLUG}_closure_race_cw.kn5", f"{SLUG}_closure_race_acw.kn5")
    for f in ("CREDITS.txt", "LICENSES.md"):
        t = (texts / "full" / f).read_text(encoding="utf-8")
        assert "K-rail" in t and "Kevin" in t and all(k in t for k in kn5s), f
        assert "personal use only" not in t.split("K-rail")[1][:400], f"{f}: the K-rail is not a personal-use blocker"
    readme = (texts / "full" / "README.txt").read_text(encoding="utf-8")
    for frag in ("Alvarado-wide lane", "own side of every", "I-8 bridge deck", "three corners", "closing off the"):
        assert frag in readme, frag
    assert "between the carriageways" not in readme, "the retired 0047 centre-chain wording"


def test_cc0_texts_render_street_only_by_default_and_with_race_on_request():
    texts = pr.TRACK_DIR / "release"
    kn5s = (f"{SLUG}_race.kn5", f"{SLUG}_closure_race_cw.kn5", f"{SLUG}_closure_race_acw.kn5")
    for f in ("CREDITS.txt", "LICENSES.md", "README.txt"):
        raw = (texts / "cc0" / f).read_bytes().decode("utf-8")
        street, race = pr.render_variant(raw, False), pr.render_variant(raw, True)
        assert "[[" not in street and "[[" not in race, f
        if f != "README.txt":
            assert "K-rail" not in street, f                                   # the default package has no race layout
            assert "K-rail" in race and all(k in race for k in kn5s), f        # --with-race credits every race kn5
        else:
            assert "not part of this download" in street and "Race — Clockwise" not in street
            assert "Race — Clockwise" in race and "Race — Anticlockwise" in race and "not part of this download" not in race
        for t in (street, race):
            assert "licence is not recorded yet" not in t, "a licence blocker in a public README"
    assert pr.render_variant("a\r\n[[with-race]]\r\nb\r\n[[/with-race]]\r\nc\r\n", False) == "a\r\nc\r\n"   # CRLF kept
    assert pr.render_variant("plain\n", True) == "plain\n"
    try:
        pr.render_variant("[[with-race]]\nb\n", True)
    except SystemExit as e:
        assert "unbalanced" in str(e)
    else:
        raise AssertionError("an unbalanced marker rendered")


def test_with_race_is_an_opt_in_flag():
    assert pr.build_parser().parse_args(["--version", "0.24.0"]).with_race is False
    assert pr.build_parser().parse_args(["--version", "0.24.0", "--with-race"]).with_race is True
    doc = pr.__doc__
    assert "THE SPLIT IS A TOOL, NOT A RULE" in doc and "Kevin's call at" in doc


def test_every_closure_kn5_leaves_the_cc0_folder_with_the_race_layouts():
    # ledger 0049: the common race kn5 + one closure kn5 per direction, plus a stale one of a retired layout
    f, cfg = _folder(THREE)
    for lid in ("race_cw", "race_acw", "race_old"):
        (f / f"{SLUG}_closure_{lid}.kn5").write_bytes(b"closure")
    removed = set(pr.strip_race_layouts(f, cfg))
    assert {f"{SLUG}_closure_race_cw.kn5", f"{SLUG}_closure_race_acw.kn5", f"{SLUG}_closure_race_old.kn5",
            f"{SLUG}_race.kn5", "models_race_cw.ini", "models_race_acw.ini"} <= removed, removed
    assert not list(f.glob(f"{SLUG}_closure_*.kn5"))
    assert (f / "models_street.ini").exists() and (f / f"{SLUG}.kn5").exists() and (f / f"{SLUG}__street.kn5").exists()

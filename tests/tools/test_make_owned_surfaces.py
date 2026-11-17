"""tools/make_owned_surfaces.py: the owned asphalt and concrete pairs. Power-of-two sizes inside the byte budget,
deterministic, seamless in u and v (the prep tiles them on a 4 m planar grid), the mean colour of the file each would
replace, little large-scale structure in the asphalt (what makes a 4 m repeat visible), an OpenGL normal map, CC0
recorded, and the committed JPEGs are what the generator paints. Plain ``test_*`` functions.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter, ImageStat

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import make_owned_surfaces as mo  # noqa: E402

SMALL = 0.125          # 256 px asphalt, 128 px concrete: same picture per metre, 1/8 the resolution


def _small():
    return {
        "asphalt_dense": mo.asphalt_dense(scale=SMALL),
        "concrete_plain": mo.concrete(scale=SMALL, seed=mo.SEEDS["concrete_plain"]),
        "concrete_aged": mo.concrete(scale=SMALL, seed=mo.SEEDS["concrete_aged"], aged=True),
    }


def _lum(im):
    return im.convert("L")


def test_sizes_are_power_of_two():
    for name, (dif, nor, hgt, _) in _small().items():
        assert dif.size == nor.size == hgt.size, name
        w, h = dif.size
        assert w == h and w & (w - 1) == 0, (name, w)        # LAWS L7
    full = {"asphalt_dense": 2048, "concrete_plain": 1024, "concrete_aged": 1024}
    for name, n in full.items():
        assert n & (n - 1) == 0 and n <= 2048


def test_deterministic():
    a, b = _small(), _small()
    for name in a:
        for k in (0, 1):
            assert ImageChops.difference(a[name][k], b[name][k]).getbbox() is None, (name, k)


def test_mean_colour_is_the_replaced_files():
    want = {"asphalt_dense": mo.MEAN_ASPHALT, "concrete_plain": mo.MEAN_CONCRETE, "concrete_aged": mo.MEAN_AGED}
    for name, (dif, *_rest) in _small().items():
        have = [v / 255.0 for v in ImageStat.Stat(dif).mean]
        for h, w in zip(have, want[name]):
            assert abs(h - w) < 0.006, (name, have, want[name])


def test_seamless_in_u_and_v():
    """the jump across the tile's edge is no bigger than an ordinary step between neighbouring pixels"""
    for name, (dif, *_rest) in _small().items():
        L = _lum(dif)
        w, h = L.size
        inner = ImageStat.Stat(ImageChops.difference(L.crop((0, 0, w - 1, h)), L.crop((1, 0, w, h)))).mean[0]
        seam_u = ImageStat.Stat(ImageChops.difference(L.crop((w - 1, 0, w, h)), L.crop((0, 0, 1, h)))).mean[0]
        seam_v = ImageStat.Stat(ImageChops.difference(L.crop((0, h - 1, w, h)), L.crop((0, 0, w, 1)))).mean[0]
        assert seam_u < 1.5 * inner and seam_v < 1.5 * inner, (name, inner, seam_u, seam_v)


def test_asphalt_has_little_large_scale_structure():
    """a repeat shows from structure bigger than ~25 cm: what is left after a 25 cm box blur stays small (the borrowed
    asphalt_cracked_diffuse.jpg measured 0.0142 of full scale there, 2026-11-16; the owned one 0.0035)"""
    dif = mo.asphalt_dense(scale=SMALL)[0]
    L = _lum(dif)
    n = L.size[0]
    k = max(3, int(round(0.25 / mo.TILE_M * n)) | 1)
    blurred = mo._wrapf(L, lambda im: im.filter(ImageFilter.BoxBlur(k // 2)), k)
    assert ImageStat.Stat(blurred).stddev[0] / 255.0 < 0.008


def test_normal_map_is_opengl_green_up():
    """a height that rises toward the top of the image tilts the normal down the image: G < 128 (ledger 0053)"""
    n = 64
    ramp = Image.new("L", (n, n))
    ramp.putdata([int(200 - 2 * y) for y in range(n) for _ in range(n)])   # bright (high) at the top row
    nor = mo._normal(ramp, strength=4.0)
    r, g, b = nor.getpixel((n // 2, n // 2))
    assert g < 120 and abs(r - 128) <= 1 and b > 200, (r, g, b)


def test_committed_files_are_the_generators_and_cc0():
    assert mo.main(["--out-dir", str(ROOT / "assets" / "textures"), "--check"]) == 0
    lic = json.loads((ROOT / "assets" / "licenses.json").read_text(encoding="utf-8"))
    rows = [r for r in lic["bundled_assets"] if "asphalt_dense_diffuse.jpg" in r.get("files", [])]
    assert len(rows) == 1
    assert rows[0]["license"] == "CC0-1.0" and "make_owned_surfaces.py" in rows[0]["source"]
    for name in mo.PAIRS:
        for suffix in ("diffuse", "normal"):
            assert f"{name}_{suffix}.jpg" in rows[0]["files"]

"""tools/make_kerb_texture.py — the worn race-kerb atlas (ledger 0053), Verification 1(d): power-of-two size inside
the byte budget, deterministic, the four rubber columns identical wherever the heaviest column has no rubber (so a
column switch only ever ADDS marks), rubber only in the tyre band, a grime joint at every 1 m block end, seamless
along the kerb, CC0 recorded — and the committed JPEGs are what the generator paints. Plain ``test_*`` functions.
"""
from __future__ import annotations

import io
import json
import random
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import make_kerb_texture as mk  # noqa: E402
import race_furniture as rf  # noqa: E402

SMALL = 0.125            # 32 px columns, 256 px tall: the same picture, 1/8 the resolution


def _cols(im, w):
    return [im.crop((c * w, 0, (c + 1) * w, im.size[1])) for c in range(rf.KERB_ATLAS_COLUMNS)]


def test_layout_is_power_of_two_and_matches_the_wrap():
    r = mk.render(SMALL)
    w, pad = r["column_px"], r["pad_px"]
    assert r["diffuse"].size == r["normal"].size == (4 * w, 8 * 32)
    full_w = rf.KERB_ATLAS_COLUMNS * rf.KERB_ATLAS_COL_PX
    full_h = int(rf.KERB_ATLAS_V_M * rf.KERB_ATLAS_PX_M)
    assert (full_w, full_h) == (1024, 2048)
    assert full_w & (full_w - 1) == 0 and full_h & (full_h - 1) == 0          # LAWS L7
    # the wrap's u for the outermost profile points stays inside each column's pad
    for lv in range(4):
        lo, hi = rf.kerb_atlas_u(lv, 0.0) * full_w, rf.kerb_atlas_u(lv, 1.0) * full_w
        assert lo == lv * 256 + 8 and hi == (lv + 1) * 256 - 8, (lo, hi)


def test_columns_differ_only_by_rubber_and_each_level_adds_to_the_last():
    r = mk.render(SMALL)
    w = r["column_px"]
    a = r["alphas"]
    assert ImageStat.Stat(a[0]).extrema[0] == (0, 0)
    for lv in range(1, 4):
        assert ImageChops.subtract(a[lv - 1], a[lv]).getbbox() is None, lv     # alpha_c >= alpha_{c-1} everywhere
        assert ImageStat.Stat(a[lv]).mean[0] > ImageStat.Stat(a[lv - 1]).mean[0]
    cols = _cols(r["diffuse"], w)
    clean = a[3].point(lambda p: 255 if p == 0 else 0)                        # where even level 3 has no rubber
    for c in cols[1:]:
        d = ImageChops.difference(cols[0], c).convert("L")
        assert ImageChops.multiply(d, clean).getbbox() is None                 # identical paint, chips, joints
    # rubber lives in the tyre band (the lane half): nothing past 60 % of the profile
    pad = r["pad_px"]
    x_cut = int(pad + 0.6 * (w - 2 * pad)) + 1
    assert a[3].crop((x_cut, 0, w, a[3].size[1])).getbbox() is None


def test_joints_at_every_block_end_and_seamless_along_the_kerb():
    r = mk.render(0.25)
    w = r["column_px"]
    col0 = _cols(r["diffuse"], w)[0].convert("L")
    h = col0.size[1]
    block = h // int(rf.KERB_ATLAS_V_M / rf.KERB_BLOCK_M)
    inner = (r["pad_px"] + 2, w - r["pad_px"] - 2)

    def row_mean(y):
        return ImageStat.Stat(col0.crop((inner[0], y % h, inner[1], y % h + 1))).mean[0]
    for b in range(8):
        joint = row_mean(b * block)
        centre = row_mean(b * block + block // 2)
        assert joint < 0.8 * centre and joint < 80, (b, joint, centre)          # the grime-filled joint
    # periodic along v: the joint at the wrap (v = 0 = 8 m) is drawn exactly like every other joint ...
    rel = r["joints"]
    rolled = Image.new("L", rel.size)
    rolled.paste(rel.crop((0, block, w, h)), (0, 0))
    rolled.paste(rel.crop((0, 0, w, block)), (0, h - block))
    assert ImageChops.difference(rel, rolled).getbbox() is None
    # ... and the colour steps across it (white block 7 -> red block 0) like across the interior joint 3 -> 4

    def step(y0, y1):
        return ImageStat.Stat(ImageChops.difference(col0.crop((inner[0], y0, inner[1], y0 + 1)),
                                                    col0.crop((inner[0], y1, inner[1], y1 + 1)))).mean[0]
    wrap, interior = step(h - 2, 2), step(4 * block - 2, 4 * block + 2)
    assert abs(wrap - interior) < 25, (wrap, interior)


def test_outer_face_is_the_same_in_every_column():
    """the wrap pins the 5 cm outer face to column 0 (race_furniture.KERB_OUTER_FACE_COLUMN, a seam then costs 4
    render vertices, not 6): that is only invisible if every column paints the outer face identically — colour AND
    relief"""
    assert rf.KERB_OUTER_FACE_COLUMN == 0
    r = mk.render(0.5)
    w, pad = r["column_px"], r["pad_px"]
    u0 = rf.kerb_profile_u()[2]                                          # outer top edge: the face is u0..1
    x0 = int(pad + u0 * (w - 2 * pad)) - 2
    for im in (r["diffuse"], r["normal"]):
        cols = _cols(im, w)
        ref = cols[0].crop((x0, 0, w - pad, im.size[1]))
        for c in cols[1:]:
            assert ImageChops.difference(ref, c.crop((x0, 0, w - pad, im.size[1]))).getbbox() is None


def test_normal_map_is_opengl_green_up():
    """OpenGL like every map in assets/textures (SOURCES.txt): a surface rising toward the BOTTOM of the image tilts
    its normal up the image (G > 128); rising to the right tilts it left (R < 128). Pins PIL's vertical kernel flip,
    which made the first cut DirectX (ledger 0053 verifier: G ~223 above each joint, ~33 below)."""
    down = Image.new("L", (16, 16))
    down.putdata([128 + 4 * (y - 8) for y in range(16) for x in range(16)])
    right = Image.new("L", (16, 16))
    right.putdata([128 + 4 * (x - 8) for y in range(16) for x in range(16)])
    r, g = mk.normal_rg(down, 1.0)
    assert g.getpixel((8, 8)) > 150 and abs(r.getpixel((8, 8)) - 128) <= 1, (r.getpixel((8, 8)), g.getpixel((8, 8)))
    r, g = mk.normal_rg(right, 1.0)
    assert r.getpixel((8, 8)) < 106 and abs(g.getpixel((8, 8)) - 128) <= 1, (r.getpixel((8, 8)), g.getpixel((8, 8)))


def test_joints_are_grooves_in_the_normal_map():
    """a joint is a groove: just ABOVE it (smaller row) the surface falls toward the joint, so the normal tilts down
    the image (G < 128); just BELOW it the normal tilts up (G > 128). Checked on the generator's render and on the
    committed JPEG, every column, every joint."""
    r = mk.render(0.25)
    w = r["column_px"]
    h = r["normal"].size[1]
    block = h // int(rf.KERB_ATLAS_V_M / rf.KERB_BLOCK_M)
    committed = Image.open(ROOT / "assets" / "textures" / mk.NORMAL_NAME).convert("RGB")
    for im, cw, blk in ((r["normal"], w, block), (committed, rf.KERB_ATLAS_COL_PX, committed.size[1] // 8)):
        g = im.getchannel("G")
        hh = im.size[1]
        for c in range(rf.KERB_ATLAS_COLUMNS):
            x0, x1 = c * cw + cw // 3, c * cw + cw // 2           # the flat top, in the tyre band
            for b in range(8):
                y = b * blk
                k = max(1, round(3 * blk / 256))                  # ~1.2 cm: the groove's flanks
                above = ImageStat.Stat(g.crop((x0, (y - k) % hh, x1, (y - k) % hh + k))).mean[0]
                below = ImageStat.Stat(g.crop((x0, y + 1, x1, y + 1 + k))).mean[0]
                assert above < 110 and below > 146, (im.size, c, b, above, below)


def test_noise_is_periodic_and_seeded():
    a = mk._noise(random.Random(7), 8, 16, 32, 128, blur=1.0)
    b = mk._noise(random.Random(7), 8, 16, 32, 128, blur=1.0)
    assert a.tobytes() == b.tobytes()
    steps = [ImageStat.Stat(ImageChops.difference(a.crop((0, y, 32, y + 1)), a.crop((0, y + 1, 32, y + 2)))).mean[0]
             for y in range(126)]
    wrap = ImageStat.Stat(ImageChops.difference(a.crop((0, 127, 32, 128)), a.crop((0, 0, 32, 1)))).mean[0]
    assert wrap <= max(steps) + 1, (wrap, max(steps))


def test_deterministic_and_within_budget():
    d1, n1, _ = mk.paint(SMALL)
    d2, n2, _ = mk.paint(SMALL)
    assert d1 == d2 and n1 == n2
    assert mk.paint(SMALL, seed=54)[0] != d1


def test_committed_files_are_the_generators_and_cc0():
    tex = ROOT / "assets" / "textures"
    for name in (mk.DIFFUSE_NAME, mk.NORMAL_NAME):
        p = tex / name
        assert p.exists(), p
        assert p.stat().st_size <= mk.MAX_BYTES, (name, p.stat().st_size)
        im = Image.open(p)
        assert im.format == "JPEG" and im.size == (1024, 2048), (name, im.format, im.size)
    # what the generator paints today (pixels, so a different libjpeg build does not flip the test)
    dif, nor, _ = mk.paint()
    for name, data in ((mk.DIFFUSE_NAME, dif), (mk.NORMAL_NAME, nor)):
        fresh = Image.open(io.BytesIO(data)).convert("RGB")
        have = Image.open(tex / name).convert("RGB")
        mad = sum(ImageStat.Stat(ImageChops.difference(fresh, have)).mean) / 3
        assert mad < 1.0, (name, mad)                    # re-run tools/make_kerb_texture.py after changing it
    lic = json.loads((ROOT / "assets" / "licenses.json").read_text(encoding="utf-8"))
    rows = [a for a in lic["bundled_assets"] if mk.DIFFUSE_NAME in a.get("files", [])]
    assert len(rows) == 1 and set(rows[0]["files"]) == {mk.DIFFUSE_NAME, mk.NORMAL_NAME}
    assert rows[0]["license"] == "CC0-1.0" and "make_kerb_texture.py" in rows[0]["source"]

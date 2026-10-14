"""scripts/geometry/terrain_tiers.py — tier_options.frame.pin (ledger 0054 P0 step 6, 2026-10-14).

The lattice frame is computed from the PINNED anchor (the installed heightfield meta's rounded bbox) shifted by whole
heightfield cells, never from a regrown meta's own anchor:
- absent pin: unchanged (every other track); pin with offsets 0 on the installed meta: today's frame, bit for bit;
- pin with offsets on a meta grown by those cells: every old lattice key lands, re-keyed by pin_key_shift, on the
  same ground (float rounding only), and the pinned frame does not depend on how the grown meta was rounded;
- a meta whose recorded growth or anchor disagrees with the pin, or a spacing mismatch, is a ValueError;
- the committed San Diego config pins the installed v0.18.0 meta with offsets 0 (P2 moves them, with the grown grid
  and the re-keyed cache, in one change).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.geometry import terrain_tiers as tt  # noqa: E402

TRACK = ROOT / "tracks" / "san-diego-lake-murray"
ORIGIN = {"lon": -117.0, "lat": 32.8, "elev_m": 100.0}
LEVELS, BASE = [40.0, 20.0, 5.0], 2.5


def _meta(round6=True):
    s, w, n, e = 32.79, -117.012, 32.81, -116.988
    sp = 40.0
    mid = (s + n) / 2
    gy, gx = sp / 111_000.0, sp / (111_000.0 * math.cos(math.radians(mid)))
    b = [round(v, 6) for v in (s, w, n, e)] if round6 else [s, w, n, e]
    return {"bbox_swne": b, "nx": int((e - w) / gx) + 1, "ny": int((n - s) / gy) + 1, "spacing_m": sp}


def _grown(meta, rn, cw, rounded=False):
    bs, bw, bn, be = meta["bbox_swne"]
    sp = meta["spacing_m"]
    mid = (bs + bn) / 2
    gy, gx = sp / 111_000.0, sp / (111_000.0 * math.cos(math.radians(mid)))
    b = [bs - rn * gy, bw - cw * gx, bn + rn * gy, be]
    if rounded:
        b = [round(v, 6) for v in b]
    return {"bbox_swne": b, "nx": meta["nx"] + cw, "ny": meta["ny"] + 2 * rn, "spacing_m": sp,
            "grid_grow": {"rows_n": rn, "rows_s": rn, "cols_w": cw, "cols_e": 0}, "base_bbox_swne": meta["bbox_swne"]}


def test_pin_with_zero_offsets_is_todays_frame_bit_for_bit():
    meta = _meta()
    a = tt.Frame.heightfield(meta, ORIGIN, 2, LEVELS, BASE)
    b = tt.Frame.heightfield(meta, ORIGIN, 2, LEVELS, BASE,
                             pin={"bbox_swne": meta["bbox_swne"], "spacing_m": 40.0, "rows_n": 0, "cols_w": 0})
    assert a.to_json() == b.to_json()
    assert tt.pin_key_shift(None, 2, 8) == (0, 0) and tt.pin_key_shift({"rows_n": 0, "cols_w": 0}, 2, 8) == (0, 0)


def test_a_grown_meta_under_the_pin_keeps_every_node_on_its_ground():
    meta = _meta()
    old = tt.Frame.heightfield(meta, ORIGIN, 2, LEVELS, BASE)
    pin = {"bbox_swne": meta["bbox_swne"], "spacing_m": 40.0, "rows_n": 37, "cols_w": 26}
    kx, kz = tt.pin_key_shift(pin, 2, 8)
    assert (kx, kz) == (26 * 16, 37 * 16)
    for rounded in (False, True):                      # full-precision or re-rounded grown meta: the same frame
        new = tt.Frame.heightfield(_grown(meta, 37, 26, rounded), ORIGIN, 2, LEVELS, BASE, pin=pin)
        assert new.ux == old.ux and new.uz == old.uz
        for I, J in ((0, 0), (5, -7), (400, -900), (-3, 12), (1965, -1487)):
            assert abs(old.x0 + I * old.ux - (new.x0 + (I + kx) * new.ux)) < 1e-9
            assert abs(old.z0 + J * old.uz - (new.z0 + (J - kz) * new.uz)) < 1e-9
    a = tt.Frame.heightfield(_grown(meta, 37, 26, False), ORIGIN, 2, LEVELS, BASE, pin=pin)
    b = tt.Frame.heightfield(_grown(meta, 37, 26, True), ORIGIN, 2, LEVELS, BASE, pin=pin)
    assert a.to_json() == b.to_json()
    # without the pin the re-rounded meta moves the anchor (up to ~5 cm): the reason the pin exists
    c = tt.Frame.heightfield(_grown(meta, 37, 26, True), ORIGIN, 2, LEVELS, BASE)
    assert a.to_json() != c.to_json()


def test_the_pin_and_the_meta_must_agree():
    meta = _meta()
    pin0 = {"bbox_swne": meta["bbox_swne"], "spacing_m": 40.0, "rows_n": 0, "cols_w": 0}
    bad = [
        (_grown(meta, 37, 26), pin0, "disagree"),                                 # grown grid, pin not moved
        (meta, dict(pin0, rows_n=37, cols_w=26), "disagree"),                     # pin moved, grid not grown
        (dict(_grown(meta, 37, 26), bbox_swne=[v + 0.001 for v in _grown(meta, 37, 26)["bbox_swne"]]),
         dict(pin0, rows_n=37, cols_w=26), "not grown by whole cells"),          # anchor off the pinned one
        (meta, dict(pin0, spacing_m=20.0), "spacing_m"),
    ]
    for m, p, why in bad:
        try:
            tt.Frame.heightfield(m, ORIGIN, 2, LEVELS, BASE, pin=p)
        except ValueError as e:
            assert why in str(e), (why, str(e))
        else:
            raise AssertionError(f"accepted: {why}")


def test_tierspec_passes_the_pin_through_and_other_tracks_are_untouched():
    meta = _meta()
    base = {"tiers": [{"within_m": 60.0, "cell_m": 5.0}, {"within_m": 300.0, "cell_m": 20.0}, {"cell_m": 40.0}],
            "far_extent": {"bbox_swne": meta["bbox_swne"]}}
    plain = tt.TierSpec(dict(base, tier_options={"frame": {"kind": "heightfield", "upsample": 2}}), ORIGIN)
    pinned = tt.TierSpec(dict(base, tier_options={"frame": {"kind": "heightfield", "upsample": 2, "pin": {
        "bbox_swne": meta["bbox_swne"], "spacing_m": 40.0, "rows_n": 0, "cols_w": 0}}}), ORIGIN)
    assert plain.frame(meta).to_json() == pinned.frame(meta).to_json()
    origin_framed = tt.TierSpec(dict(base, tier_options={}), ORIGIN)
    assert origin_framed.frame(None).to_json() == [0.0, 0.0, origin_framed.base_m, origin_framed.base_m]


def test_committed_config_pins_the_installed_meta_with_zero_offsets():
    cfg = json.loads((TRACK / "track.config.json").read_text(encoding="utf-8"))
    meta = json.loads((TRACK / "data" / "heightfield.meta.json").read_text(encoding="utf-8"))
    pin = cfg["terrain"]["tier_options"]["frame"]["pin"]
    assert pin["bbox_swne"] == meta["bbox_swne"] == [32.771983, -117.069563, 32.805287, -117.017103]
    assert pin["spacing_m"] == meta["spacing_m"] and pin["rows_n"] == 0 and pin["cols_w"] == 0
    assert "grid_grow" not in meta                       # the installed grid: P2 grows it with the pin and the cache
    origin = json.loads((TRACK / "data" / "centerline.local.json").read_text(encoding="utf-8"))["origin"]
    spec = tt.TierSpec(cfg["terrain"], origin)
    unpinned = tt.Frame.heightfield(meta, origin, 2, spec.levels, spec.base_m)
    assert spec.frame(meta).to_json() == unpinned.to_json()
    # the cached 3DEP samples were taken on exactly this frame
    import gzip
    prov = json.loads(gzip.decompress((TRACK / "data" / "terrain.samples.json.gz").read_bytes()))["_provenance"]
    assert all(abs(a - b) < 1e-9 for a, b in zip(prov["lattice_frame"], spec.frame(meta).to_json()))

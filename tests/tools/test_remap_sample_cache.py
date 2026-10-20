"""tools/remap_sample_cache.py — re-key the tiered 3DEP cache for a heightfield grown by whole cells (ledger 0054 P0
step 6), with its identity proof. A synthetic project (2 x 2 km, a heightfield frame, a cache of base + fine keys
written by terrain_sample.SampleCache); no network.

- every key moves by (+cols_w*u, -rows_n*u) base units (u = upsample x per), fine keys by BREAK_FINE times that;
- every node lands on the same lon/lat (<= 1e-9 deg), the h_cm lists are byte-identical, the re-keyed cache loads
  under the pinned frame of the grown meta (the frame terrain_sample will compute in P2) and nowhere else;
- refusals: a grown meta, a pin that already carries offsets, --out = the input without --in-place, a relative project.
"""
from __future__ import annotations

import contextlib
import gzip
import importlib.util
import io
import json
import math
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.elevation import terrain_sample as ts  # noqa: E402
from scripts.geometry import terrain_tiers as tt  # noqa: E402

ORIGIN = {"lon": -117.0, "lat": 32.8, "elev_m": 100.0}


def _tool():
    spec = importlib.util.spec_from_file_location("_tool_remap_sample_cache", ROOT / "tools" / "remap_sample_cache.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _project(d: Path, pin=None):
    m_lon, m_lat = tt.meters_per_degree(ORIGIN["lat"])
    s, w, n, e = 32.8 - 1000 / m_lat, -117.0 - 1000 / m_lon, 32.8 + 1000 / m_lat, -117.0 + 1000 / m_lon
    sp = 40.0
    mid = (s + n) / 2
    gy, gx = sp / 111_000.0, sp / (111_000.0 * math.cos(math.radians(mid)))
    meta = {"bbox_swne": [round(v, 6) for v in (s, w, n, e)], "nx": int((e - w) / gx) + 1,
            "ny": int((n - s) / gy) + 1, "spacing_m": sp, "margin_m": 150.0, "row0": "north"}
    frame = {"kind": "heightfield", "upsample": 2}
    if pin is not None:
        frame["pin"] = pin
    terrain = {"tiers": [{"within_m": 60.0, "cell_m": 5.0}, {"within_m": 300.0, "cell_m": 20.0}, {"cell_m": 40.0}],
               "tier_options": {"frame": frame}, "far_extent": {"bbox_swne": meta["bbox_swne"]}}
    (d / "data").mkdir(parents=True)
    (d / "track.config.json").write_text(json.dumps({"terrain": terrain, "loop": False}), encoding="utf-8")
    (d / "data" / "heightfield.meta.json").write_text(json.dumps(meta), encoding="utf-8")
    (d / "data" / "centerline.local.json").write_text(json.dumps(
        {"origin": ORIGIN, "points_xyz_m": [[float(x), 0.0, 0.0] for x in range(-400, 401, 5)],
         "widths_m": [10.0] * 161}), encoding="utf-8")
    spec = tt.TierSpec(terrain, ORIGIN)
    fr = spec.frame(meta)
    cache = ts.SampleCache(d / "data" / ts.SAMPLES, spec, fr)
    for I in range(-60, 61, 3):
        for J in range(-50, 51, 5):
            cache.h[(I, J)] = round(100.0 + 0.01 * I - 0.02 * J + (I * J % 7) * 0.13, 2)
    for I in range(-100, 100, 7):
        cache.fine[(I, 3 * tt.BREAK_FINE)] = round(90.0 + 0.003 * I, 2)
    cache.save()
    return meta, spec, fr


def _run(mod, argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        try:
            rc = mod.main(argv)
        except (SystemExit, ValueError) as e:
            rc = e
    return rc, out.getvalue()


def test_rekey_moves_keys_by_whole_cells_and_keeps_every_sample_on_its_ground():
    mod = _tool()
    with tempfile.TemporaryDirectory() as t:
        proj = Path(t) / "p"
        meta, spec, old = _project(proj)
        src = proj / "data" / ts.SAMPLES
        before = gzip.decompress(src.read_bytes())
        out = Path(t) / "out" / "terrain.samples.json.gz"
        rc, log = _run(mod, [str(proj), "--rows-n", "37", "--cols-w", "26", "--out", str(out), "--samples", "200"])
        assert rc == 0 and "PASS" in log, log
        assert gzip.decompress(src.read_bytes()) == before            # the input is never touched
        rep = json.loads(Path(str(out) + ".proof.json").read_text(encoding="utf-8"))
        u = 2 * 8                                                      # upsample 2 x 8 base units per 20 m cell
        assert rep["key_shift_base"] == [26 * u, -37 * u]
        assert rep["key_shift_fine"] == [26 * u * tt.BREAK_FINE, -37 * u * tt.BREAK_FINE]
        assert rep["max_position_diff_deg_all_keys"] <= 1e-9 and rep["max_position_diff_deg_fine_keys"] <= 1e-9
        assert rep["h_cm_lists_byte_identical"] and rep["random_nodes"] == 200 and not rep["random_nodes_failing"]
        old_d = json.loads(before)
        new_d = json.loads(gzip.decompress(out.read_bytes()))
        assert new_d["h_cm"] == old_d["h_cm"] and new_d["fine"]["h_cm"] == old_d["fine"]["h_cm"]
        assert new_d["I"] == [i + 26 * u for i in old_d["I"]] and new_d["J"] == [j - 37 * u for j in old_d["J"]]
        assert new_d["_provenance"]["remaps"][-1]["key_shift_base"] == [26 * u, -37 * u]
        # the re-keyed cache loads under the pinned frame of the grown meta, and the old frame refuses it
        pin = {"bbox_swne": meta["bbox_swne"], "spacing_m": 40.0, "rows_n": 37, "cols_w": 26}
        new = tt.Frame.heightfield(mod.grown_meta(meta, 37, 37, 26, 0), ORIGIN, 2, spec.levels, spec.base_m, pin=pin)
        assert new.to_json() == rep["new_frame"]
        c = ts.SampleCache(out, spec, new)
        assert len(c.h) == len(old_d["I"]) and len(c.fine) == len(old_d["fine"]["I"])
        try:
            ts.SampleCache(out, spec, old)
        except SystemExit as e:
            assert "lattice/origin changed" in str(e.code)
        else:
            raise AssertionError("the re-keyed cache loaded under the old frame")


def test_refusals():
    mod = _tool()
    with tempfile.TemporaryDirectory() as t:
        proj = Path(t) / "p"
        meta, _spec, _fr = _project(proj)
        src = proj / "data" / ts.SAMPLES
        rc, log = _run(mod, [str(proj), "--rows-n", "1", "--cols-w", "1", "--out", str(src)])
        assert rc == 2 and "--in-place" in log
        rc, log = _run(mod, ["relative/p", "--rows-n", "1", "--cols-w", "1", "--out", str(Path(t) / "o.gz")])
        assert rc == 2 and "ABSOLUTE" in log
        rc, log = _run(mod, [str(proj), "--rows-n", "0", "--cols-w", "0", "--out", str(Path(t) / "o.gz")])
        assert rc == 2
        # an already-grown meta
        (proj / "data" / "heightfield.meta.json").write_text(json.dumps(
            dict(meta, grid_grow={"rows_n": 1, "rows_s": 1, "cols_w": 0, "cols_e": 0})), encoding="utf-8")
        rc, _log = _run(mod, [str(proj), "--rows-n", "1", "--cols-w", "1", "--out", str(Path(t) / "o.gz")])
        assert isinstance(rc, SystemExit) and "already grown" in str(rc.code)
    with tempfile.TemporaryDirectory() as t:
        proj = Path(t) / "p"
        m = _project(proj)[0]
        cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
        cfg["terrain"]["tier_options"]["frame"]["pin"] = {"bbox_swne": m["bbox_swne"], "spacing_m": 40.0,
                                                          "rows_n": 0, "cols_w": 0}
        (proj / "track.config.json").write_text(json.dumps(cfg), encoding="utf-8")
        rc, log = _run(mod, [str(proj), "--rows-n", "2", "--cols-w", "3", "--out", str(Path(t) / "o.gz")])
        assert rc == 0 and "PASS" in log, log                          # a zero-offset pin is today's frame
        cfg["terrain"]["tier_options"]["frame"]["pin"]["rows_n"] = 2
        (proj / "track.config.json").write_text(json.dumps(cfg), encoding="utf-8")
        rc, _log = _run(mod, [str(proj), "--rows-n", "2", "--cols-w", "3", "--out", str(Path(t) / "o2.gz")])
        assert isinstance(rc, ValueError) and "disagree" in str(rc)   # the config's pin and the meta disagree

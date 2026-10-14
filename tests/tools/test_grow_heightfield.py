"""tools/grow_heightfield.py (ledger 0054 P2): the installed 40 m heightfield grown by terrain.grid_grow whole cells
without re-sampling one old stake. A tiny project: a 1.2 x 0.8 km loop, its installed grid laid out by scripts-v021
heightfield.build_heightfield with a stub sampler; 3DEP stubbed (no network).

- the old block of the grown grid is the installed grid, value for value; only the added nodes are fetched; the meta is
  build_heightfield's (base_bbox, grid_grow) and the frame pin on it re-keys by whole cells;
- refused: no grid_grow, a meta already grown, an installed grid that the loop's points do not lay out, an
  elevation_scale other than 1, a fetch with --offline, a no-data answer.
"""
from __future__ import annotations

import json
import struct
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import grow_heightfield as gh  # noqa: E402

HF = gh.load_v021_heightfield()


def _project(grow=None, scale=None):
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    lon0, lat0 = -117.0, 32.8
    ring = [(lon0, lat0), (lon0 + 0.012, lat0), (lon0 + 0.012, lat0 + 0.007), (lon0, lat0 + 0.007), (lon0, lat0)]
    coords = []
    for a, b in zip(ring, ring[1:]):
        for k in range(20):
            t = k / 20
            coords.append([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t])
    coords.append(coords[0])
    gj = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"kind": "full"},
                                                     "geometry": {"type": "LineString", "coordinates": coords}}]}
    (d / "data" / "centerline.geojson").write_text(json.dumps(gj), encoding="utf-8")
    cfg = {"terrain": {}}
    if grow:
        cfg["terrain"]["grid_grow"] = grow
    if scale is not None:
        cfg["scenery"] = {"elevation_scale": scale}
    (d / "track.config.json").write_text(json.dumps(cfg), encoding="utf-8")
    # the INSTALLED grid: build_heightfield's own layout, a smooth surface of position
    real = HF.usgs_3dep
    HF.usgs_3dep = type("S", (), {"sample_points": staticmethod(lambda pts, **k: [100.0 + 3000 * (p[0] + 117) + 5000 * (p[1] - 32.8)
                                                                               for p in pts])})
    try:
        grid, meta = HF.build_heightfield([tuple(c) for c in coords], HF.HF_SPACING_M, HF.HF_MARGIN_M)
    finally:
        HF.usgs_3dep = real
    HF.write_npy(d / "data" / "heightfield.npy", grid)
    (d / "data" / "heightfield.meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return d, grid, meta


def _read(p):
    g, ny, nx = gh.read_npy(p)
    return g


def test_grow_keeps_the_installed_block_and_fetches_only_the_new_nodes():
    grow = {"rows_n": 2, "rows_s": 2, "cols_w": 3, "cols_e": 1}
    d, grid0, meta0 = _project(grow)
    asked = []

    def fetch(pts):
        asked.extend(pts)
        return [-1.0] * len(pts)

    out = d / "out"
    p = gh.grow(d, out, fetch=fetch)
    g = _read(out / "heightfield.npy")
    m = json.loads((out / "heightfield.meta.json").read_text(encoding="utf-8"))
    ny0, nx0 = meta0["ny"], meta0["nx"]
    assert (m["ny"], m["nx"]) == (ny0 + 4, nx0 + 4)
    assert all(g[j + 2][i + 3] == grid0[j][i] for j in range(ny0) for i in range(nx0))
    assert sum(1 for row in g for v in row if v == -1.0) == len(asked) == m["nx"] * m["ny"] - nx0 * ny0
    assert p["old_block_identical_to_installed"] and p["old_nodes_from_installed_grid"] == nx0 * ny0
    assert m["grid_grow"] == grow and m["base_bbox_swne"] == meta0["bbox_swne"]
    assert (m["base_nx"], m["base_ny"]) == (nx0, ny0)
    # the written files are heightfield.py's own (its writer, its meta)
    assert (out / "heightfield.npy").read_bytes()[:6] == b"\x93NUMPY"
    assert json.loads((out / "heightfield.grow.proof.json").read_text())["new_nodes_from_3dep"] == len(asked)


def _refused(fn, word):
    try:
        fn()
    except SystemExit as e:
        assert word in str(e), str(e)
    else:
        raise AssertionError(f"expected a refusal mentioning {word!r}")


def test_refusals():
    d, _g, _m = _project(None)
    _refused(lambda: gh.grow(d, d / "o", fetch=lambda p: [0.0] * len(p)), "grid_grow")
    d, _g, _m = _project({"rows_n": 1, "rows_s": 1}, scale=0.5)
    _refused(lambda: gh.grow(d, d / "o", fetch=lambda p: [0.0] * len(p)), "elevation_scale")
    d, _g, _m = _project({"rows_n": 1, "rows_s": 1})
    _refused(lambda: gh.grow(d, d / "o", offline=True), "--offline")
    _refused(lambda: gh.grow(d, d / "o", fetch=lambda p: [None] * len(p)), "no value")
    gh.grow(d, d / "data", fetch=lambda p: [0.0] * len(p))       # grown in place: a second growth is refused
    _refused(lambda: gh.grow(d, d / "o", fetch=lambda p: [0.0] * len(p)), "already grown")
    d, _g, meta = _project({"rows_n": 1, "rows_s": 1})
    meta["nx"] += 1                                             # an installed grid these points did not lay out
    (d / "data" / "heightfield.meta.json").write_text(json.dumps(meta), encoding="utf-8")
    _refused(lambda: gh.grow(d, d / "o", fetch=lambda p: [0.0] * len(p)), "heightfield.npy is")


def test_committed_grid_is_the_installed_v018_grid_grown():
    """the committed San Diego grid: its old block is v0.18.0's grid (test_v021_heightfield_grow md5-checks it), the
    proof says every old node came from it and 13,444 new ones from 3DEP"""
    track = ROOT / "tracks" / "san-diego-lake-murray"
    m = json.loads((track / "data" / "heightfield.meta.json").read_text(encoding="utf-8"))
    proof = json.loads((track / "source" / "expansion" / "p2-proofs" / "heightfield.grow.proof.json").read_text())
    assert m["grid_grow"] == {"rows_n": 37, "rows_s": 37, "cols_w": 26, "cols_e": 0}
    assert proof["old_nodes_from_installed_grid"] == 123 * 93 and proof["new_nodes_from_3dep"] == 13444
    assert proof["old_block_identical_to_installed"] and proof["grown"]["nx"] * proof["grown"]["ny"] == 24883
    raw = (track / "data" / "heightfield.npy").read_bytes()
    hl = struct.unpack("<H", raw[8:10])[0]
    assert "(167, 149)" in raw[10:10 + hl].decode("latin1")

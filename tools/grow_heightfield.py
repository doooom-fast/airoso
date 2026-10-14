"""Grow the installed 40 m heightfield by whole cells WITHOUT re-sampling one old stake (ledger 0054 P2, EXPANSION-PLAN
P0 step 6 / P2: "the grown heightfield, the pin's 37 / 26 and the re-keyed cache land in one change").

scripts-v021 ``elevation/heightfield.py`` ``build_heightfield(grow=...)`` lays the grown grid out from the loop's own
points so that every old node is sampled at EXACTLY the position it always was (P0 proof C). Its ``build()`` would
also re-sample the whole centreline and every node from 3DEP today; this tool does neither. It runs the same
``build_heightfield`` twice with a sampler that answers from data:

  1. ungrown, to read back the installed grid's own sample positions: the meta it writes must be the installed
     ``heightfield.meta.json`` (and the grid its dims), else the installed grid did not come from these points;
  2. grown by ``terrain.grid_grow``: every position that is an old node (bit for bit) takes the INSTALLED value,
     every other one is fetched from USGS 3DEP 1 m (scripts.elevation.usgs_3dep._sample_batch: TLS verified, 4
     tries, no silent fill - a no-data point aborts).

Writes ``heightfield.npy`` + ``heightfield.meta.json`` exactly as heightfield.py writes them (its own writer) into
``--out-dir`` (default: the project's data/), plus ``heightfield.grow.proof.json`` (the old block byte-identical to the
installed grid, the node counts, the requests, the provenance). Refuses a meta that is already grown, an
``elevation_scale`` other than 1 (the installed values would be scaled and the new ones not) and, ``--offline``, any
fetch.

    python tools/grow_heightfield.py <ABSOLUTE-project-dir> [--out-dir DIR] [--offline]

The project needs track.config.json (``terrain.grid_grow``), data/centerline.geojson (the ``full`` feature: the points
the grid was laid out from) and the installed data/heightfield.npy + .meta.json.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import struct
import sys
import time
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AIROSO))

from scripts.elevation import usgs_3dep  # noqa: E402  (TLS: scripts.tls.https_context)

V021_HF = AIROSO / "tracks" / "san-diego-lake-murray" / "scripts-v021" / "elevation" / "heightfield.py"


def load_v021_heightfield(path: Path = V021_HF):
    """scripts-v021's heightfield.py BY PATH (its `scripts.*` imports resolve to airoso's engine: usgs_3dep with TLS,
    gps.centerline.haversine); never registered as `scripts`"""
    spec = importlib.util.spec_from_file_location("_v021_heightfield", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read_npy(path: Path):
    raw = path.read_bytes()
    if raw[:6] != b"\x93NUMPY":
        raise SystemExit(f"[grow] {path} is not an .npy file")
    hl = struct.unpack("<H", raw[8:10])[0]
    header = raw[10:10 + hl].decode("latin1")
    if "'<f8'" not in header or "False" not in header:
        raise SystemExit(f"[grow] {path}: expected a C-order float64 grid, header {header.strip()}")
    shape = header.split("'shape': (")[1].split(")")[0]
    ny, nx = (int(v) for v in shape.replace(" ", "").split(",")[:2])
    vals = struct.unpack("<%dd" % (nx * ny), raw[10 + hl:10 + hl + 8 * nx * ny])
    return [list(vals[j * nx:(j + 1) * nx]) for j in range(ny)], ny, nx


def fetch_3dep(points, chunk: int = 450, workers: int = 4):
    """3DEP 1 m at each (lon, lat), in order: usgs_3dep._sample_batch (TLS verified, 4 tries) in chunks, never the
    filling sample_points - a no-data point stays None and the caller aborts (L2)"""
    from concurrent.futures import ThreadPoolExecutor
    chunks = [points[a:a + chunk] for a in range(0, len(points), chunk)]
    out = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for vals in ex.map(lambda c: usgs_3dep._sample_batch(c, retries=4), chunks):
            out += vals
    return [None if v is None else float(v) for v in out]          # unrounded, as the installed grid


def grow(proj: Path, out_dir: Path, offline: bool = False, fetch=None) -> dict:
    """the grown grid + meta written to ``out_dir``; returns the proof. ``fetch`` (tests) replaces the 3DEP sampler."""
    hf = load_v021_heightfield()
    data = proj / "data"
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    g = hf.grid_grow_spec(cfg)
    if not g:
        raise SystemExit("[grow] track.config.json has no terrain.grid_grow: nothing to grow")
    escale = float((cfg.get("scenery") or {}).get("elevation_scale", 1.0))
    if escale != 1.0:
        raise SystemExit(f"[grow] scenery.elevation_scale {escale}: the installed grid is scaled, fetched nodes would not "
                         f"be (not supported)")
    meta0 = json.loads((data / "heightfield.meta.json").read_text(encoding="utf-8"))
    if meta0.get("grid_grow"):
        raise SystemExit(f"[grow] data/heightfield.meta.json is already grown ({meta0['grid_grow']}): grow from the "
                         f"installed (ungrown) grid")
    grid0, ny0, nx0 = read_npy(data / "heightfield.npy")
    if (ny0, nx0) != (meta0["ny"], meta0["nx"]):
        raise SystemExit(f"[grow] heightfield.npy is {ny0} x {nx0}, its meta says {meta0['ny']} x {meta0['nx']}")
    gj = json.loads((data / "centerline.geojson").read_text(encoding="utf-8"))
    full = next(f for f in gj["features"] if f["properties"].get("kind") == "full")
    coords = [(lon, lat) for lon, lat in full["geometry"]["coordinates"]]
    sp, margin = hf.HF_SPACING_M, hf.HF_MARGIN_M

    # 1. the installed grid's own positions (no fetch): the ungrown layout must reproduce the installed meta
    seen = {}

    def capture(points, **_k):
        seen["points"] = list(points)
        return [0.0] * len(points)

    real = hf.usgs_3dep
    try:
        hf.usgs_3dep = type("S", (), {"sample_points": staticmethod(capture)})
        _g, meta_re = hf.build_heightfield(list(coords), sp, margin, grow=None)
    finally:
        hf.usgs_3dep = real
    if meta_re != meta0:
        raise SystemExit(f"[grow] the loop's points lay the ungrown grid out as {meta_re}, not the installed {meta0}: "
                         f"the installed grid did not come from data/centerline.geojson")
    pts0 = seen["points"]
    if len(pts0) != nx0 * ny0:
        raise SystemExit("[grow] position count mismatch")
    lookup = {p: grid0[k // nx0][k % nx0] for k, p in enumerate(pts0)}
    if len(lookup) != len(pts0):
        raise SystemExit("[grow] two installed nodes share a position")

    # 2. the grown layout: old positions take the installed value, the rest is fetched
    stat = {"old": 0, "new": 0, "requests": 0}
    t0 = time.time()

    def serve(points, **_k):
        out = [None] * len(points)
        todo = []
        for k, p in enumerate(points):
            v = lookup.get(p)
            if v is None:
                todo.append(k)
            else:
                out[k] = v
        stat["old"], stat["new"] = len(points) - len(todo), len(todo)
        if todo and offline:
            raise SystemExit(f"[grow] --offline: {len(todo)} new nodes would need 3DEP")
        if todo:
            pts = [points[k] for k in todo]
            stat["requests"] = -(-len(pts) // 450)
            vals = (fetch or fetch_3dep)(pts)
            bad = [k for k, v in zip(todo, vals) if v is None]
            if bad:
                raise SystemExit(f"[grow] 3DEP returned no value at {len(bad)} new nodes - no silent fill (L2)")
            for k, v in zip(todo, vals):
                out[k] = float(v)
        return out

    try:
        hf.usgs_3dep = type("S", (), {"sample_points": staticmethod(serve)})
        grid, meta = hf.build_heightfield(list(coords), sp, margin, grow=g)
    finally:
        hf.usgs_3dep = real
    rn, cw = g["rows_n"], g["cols_w"]
    old_ok = all(grid[j + rn][i + cw] == grid0[j][i] for j in range(ny0) for i in range(nx0))
    if not old_ok or stat["old"] != nx0 * ny0:
        raise SystemExit(f"[grow] the old block is not the installed grid ({stat['old']} of {nx0 * ny0} old nodes "
                         f"found at their positions)")
    out_dir.mkdir(parents=True, exist_ok=True)
    hf.write_npy(out_dir / "heightfield.npy", grid)
    (out_dir / "heightfield.meta.json").write_text(json.dumps(meta), encoding="utf-8")
    proof = {"what": "ledger 0054 P2: the installed 40 m heightfield grown by whole cells (tools/grow_heightfield.py)",
             "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
             "grid_grow": g, "installed": {"nx": nx0, "ny": ny0, "bbox_swne": meta0["bbox_swne"]},
             "grown": {"nx": meta["nx"], "ny": meta["ny"], "bbox_swne": meta["bbox_swne"]},
             "nodes": meta["nx"] * meta["ny"], "old_nodes_from_installed_grid": stat["old"],
             "new_nodes_from_3dep": stat["new"], "requests": stat["requests"],
             "old_block_identical_to_installed": old_ok,
             "positions": "scripts-v021 heightfield.build_heightfield(grow=...): every old node at its bit-identical "
                          "position (looked up by exact float pair)",
             "source": "USGS 3DEP 1 m bare earth, ImageServer getSamples (scripts.elevation.usgs_3dep, TLS verified)",
             "seconds": round(time.time() - t0, 1)}
    (out_dir / "heightfield.grow.proof.json").write_text(json.dumps(proof, indent=1), encoding="utf-8")
    return proof


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="grow the installed 40 m heightfield by terrain.grid_grow whole cells")
    ap.add_argument("project")
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args(argv)
    proj = Path(a.project)
    if not proj.is_absolute():
        print("[grow] the project must be an ABSOLUTE path")
        return 2
    out = Path(a.out_dir) if a.out_dir else proj / "data"
    p = grow(proj, out, a.offline)
    print(f"[grow] {p['installed']['nx']} x {p['installed']['ny']} -> {p['grown']['nx']} x {p['grown']['ny']} "
          f"({p['nodes']} nodes): {p['old_nodes_from_installed_grid']} from the installed grid, "
          f"{p['new_nodes_from_3dep']} from 3DEP ({p['requests']} requests); old block identical "
          f"{p['old_block_identical_to_installed']} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Re-key the tiered-terrain 3DEP cache for a heightfield grown by whole cells — with the identity proof.

Ledger 0054 P0 step 6 (EXPANSION-PLAN "Grow the 40 m heightfield without moving a single old stake", 2026-10-14).
``data/terrain.samples.json.gz`` (scripts.elevation.terrain_sample) keys every 3DEP sample by its lattice node
(I, J), placed by the lattice FRAME: x = x0 + I*ux, z = z0 + J*uz. The Lake Murray frame is anchored on the
heightfield grid's north-west node (``tier_options.frame.kind = heightfield``). Growing that grid by ``rows_n`` rows
north and ``cols_w`` columns west moves the anchor by exactly kx = cols_w * u base units west and kz = rows_n * u
north (u = base units per 40 m cell: upsample x per), so every node keeps its place on the ground and only its key
changes: (I, J) -> (I + kx, J - kz); a fine break-line key (base / BREAK_FINE units) moves by BREAK_FINE times that.
The new frame is the one ``Frame.heightfield`` computes under ``tier_options.frame.pin`` with those offsets (the
installed rounded anchor, shifted by whole cells at full precision), so a re-keyed cache loads under it and no
sample is fetched again (the naive regrowth would move the mid-latitude by +0.0065 deg, drift nodes 5 km east by
0.37 m and re-fetch ~360k samples).

THE PROOF (written to ``--proof``, exit 1 if it fails): every cached key, old frame vs new frame + re-keyed key, lies
at the same lon/lat within ``TOL_DEG`` 1e-9 deg [invented: ~0.1 mm; the float error is ~1e-13]; the re-keyed file
loads through terrain_sample.SampleCache under the new frame; its ``h_cm`` (and fine ``h_cm``) lists are the old
lists, byte for byte; and ``--samples`` (default 1,000) random old nodes (fixed seed) are re-read one by one through
both caches: same position to 1e-9 deg, identical sample.

    python tools/remap_sample_cache.py <ABSOLUTE-project-dir> --rows-n 37 --cols-w 26 --out <new.json.gz>
           [--in <cache>] [--proof <proof.json>] [--samples 1000] [--seed 54]

Reads the project's track.config.json (terrain spec, frame), data/heightfield.meta.json (the CURRENT, ungrown grid)
and the road inputs terrain_sample reads for the origin. Writes only ``--out`` and ``--proof`` (never in place
unless ``--out`` is the input path, which needs ``--in-place``). No network.
"""
from __future__ import annotations

import argparse
import gzip
import json
import random
import sys
import time
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AIROSO))

from scripts.elevation import terrain_sample as ts  # noqa: E402
from scripts.geometry import terrain_tiers as tt  # noqa: E402

TOL_DEG = 1e-9


def grown_meta(meta: dict, rows_n: int, rows_s: int, cols_w: int, cols_e: int) -> dict:
    """the meta scripts-v021 heightfield.build_heightfield writes for this growth (its full-precision bbox from the
    loop grid's rounded one, in the consumers' own cell size)"""
    import math
    bs, bw, bn, be = meta.get("base_bbox_swne") or meta["bbox_swne"]
    sp = float(meta["spacing_m"])
    mid = (bs + bn) / 2
    gy, gx = sp / 111_000.0, sp / (111_000.0 * math.cos(math.radians(mid)))
    return {"bbox_swne": [bs - rows_s * gy, bw - cols_w * gx, bn + rows_n * gy, be + cols_e * gx],
            "nx": meta["nx"] + cols_w + cols_e, "ny": meta["ny"] + rows_n + rows_s, "spacing_m": sp,
            "grid_grow": {"rows_n": rows_n, "rows_s": rows_s, "cols_w": cols_w, "cols_e": cols_e},
            "base_bbox_swne": [bs, bw, bn, be]}


def frames(spec: tt.TierSpec, meta: dict, rows_n: int, cols_w: int):
    """(old frame, new frame, pin, (kx, kz)) — the new frame is Frame.heightfield under the pin on the grown meta"""
    if spec.frame_cfg.get("kind") != "heightfield":
        raise SystemExit("[remap] tier_options.frame.kind is not 'heightfield': nothing is anchored on the grid")
    if (meta.get("grid_grow") or {}).get("rows_n") or (meta.get("grid_grow") or {}).get("cols_w"):
        raise SystemExit("[remap] data/heightfield.meta.json is already grown: remap from the installed (ungrown) meta")
    old = spec.frame(meta)
    pin0 = dict(spec.frame_cfg.get("pin") or {})
    if pin0 and (int(pin0.get("rows_n", 0)) or int(pin0.get("cols_w", 0))):
        raise SystemExit(f"[remap] the config's frame pin already carries offsets {pin0}: one growth at a time, "
                         f"from the pinned anchor with offsets 0")
    pin = {"bbox_swne": list(pin0.get("bbox_swne") or meta["bbox_swne"]),
           "spacing_m": float(pin0.get("spacing_m", meta["spacing_m"])), "rows_n": rows_n, "cols_w": cols_w}
    up = int(spec.frame_cfg.get("upsample", 1))
    new = tt.Frame.heightfield(grown_meta(meta, rows_n, rows_n, cols_w, 0), spec.origin, up, spec.levels,
                               spec.base_m, pin=pin)
    per = int(round(float(meta["spacing_m"]) / max(1, up) / spec.base_m))
    return old, new, pin, tt.pin_key_shift(pin, up, per)


def remap(proj: Path, rows_n: int, cols_w: int, src: Path, out: Path, n_samples: int = 1000, seed: int = 54) -> dict:
    proj = Path(proj).resolve()
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    _lines, origin, _files = ts.road_inputs(proj)
    spec = tt.TierSpec(cfg.get("terrain"), origin, bool(cfg.get("mirror_x", False)))
    if not spec.enabled:
        raise SystemExit("[remap] terrain.tiers not declared: no tiered cache to remap")
    meta = tt.load_heightfield_meta(proj)
    if meta is None:
        raise SystemExit("[remap] no data/heightfield.meta.json")
    old, new, pin, (kx, kz) = frames(spec, meta, rows_n, cols_w)
    old_cache = ts.SampleCache(src, spec, old)             # refuses a cache that is not on the current frame
    d = json.loads(gzip.decompress(src.read_bytes()).decode("utf-8"))
    F = tt.BREAK_FINE
    nd = {"_provenance": dict(d["_provenance"]),
          "I": [i + kx for i in d["I"]], "J": [j - kz for j in d["J"]], "h_cm": list(d["h_cm"])}
    if d.get("fine"):
        fd = d["fine"]
        nd["fine"] = {**{k: v for k, v in fd.items() if k not in ("I", "J", "h_cm")},
                      "I": [i + kx * F for i in fd["I"]], "J": [j - kz * F for j in fd["J"]], "h_cm": list(fd["h_cm"])}
    prov = nd["_provenance"]
    prov["lattice_frame"] = new.to_json()
    prov.setdefault("remaps", []).append({
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "tool": "tools/remap_sample_cache.py (ledger 0054 P0 step 6)",
        "why": "heightfield grown by whole cells (terrain.grid_grow); frame pinned (tier_options.frame.pin)",
        "rows_n": rows_n, "cols_w": cols_w, "key_shift_base": [kx, -kz], "key_shift_fine": [kx * F, -kz * F],
        "from_lattice_frame": old.to_json(), "pin": pin})
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(gzip.compress(json.dumps(nd, separators=(",", ":")).encode("utf-8"), 9, mtime=0))

    # --- the proof ---
    new_cache = ts.SampleCache(out, spec, new)             # loads under the new frame (1e-9 m lattice check)
    lonlat = spec.to_lonlat

    def pos(f, i, j, q=1.0):
        return lonlat(f.x0 + i / q * f.ux, f.z0 + j / q * f.uz)

    worst = 0.0
    for i, j in zip(d["I"], d["J"]):
        a, b = pos(old, i, j), pos(new, i + kx, j - kz)
        worst = max(worst, abs(a[0] - b[0]), abs(a[1] - b[1]))
    worst_fine = 0.0
    if d.get("fine"):
        for i, j in zip(d["fine"]["I"], d["fine"]["J"]):
            a, b = pos(old, i, j, float(F)), pos(new, i + kx * F, j - kz * F, float(F))
            worst_fine = max(worst_fine, abs(a[0] - b[0]), abs(a[1] - b[1]))
    rng = random.Random(seed)
    keys = sorted(old_cache.h)
    pick = rng.sample(keys, min(n_samples, len(keys)))
    rows, bad = [], []
    for (i, j) in pick:
        a, b = pos(old, i, j), pos(new, i + kx, j - kz)
        dd = max(abs(a[0] - b[0]), abs(a[1] - b[1]))
        same = new_cache.h.get((i + kx, j - kz)) == old_cache.h[(i, j)]
        if dd > TOL_DEG or not same:
            bad.append([i, j])
        rows.append([i, j, i + kx, j - kz, a[0], a[1], b[0], b[1], old_cache.h[(i, j)], new_cache.h.get((i + kx, j - kz))])
    h_identical = nd["h_cm"] == d["h_cm"] and (not d.get("fine") or nd["fine"]["h_cm"] == d["fine"]["h_cm"])
    rep = {"project": proj.as_posix(), "in": src.as_posix(), "out": out.as_posix(),
           "rows_n": rows_n, "cols_w": cols_w, "key_shift_base": [kx, -kz], "key_shift_fine": [kx * F, -kz * F],
           "old_frame": old.to_json(), "new_frame": new.to_json(), "pin": pin,
           "keys": len(d["I"]), "fine_keys": len((d.get("fine") or {}).get("I", [])),
           "max_position_diff_deg_all_keys": worst, "max_position_diff_deg_fine_keys": worst_fine,
           "tol_deg": TOL_DEG, "h_cm_lists_byte_identical": h_identical,
           "random_nodes": len(pick), "seed": seed, "random_nodes_failing": bad,
           "random_node_rows": {"columns": ["I", "J", "I_new", "J_new", "lon_old", "lat_old", "lon_new", "lat_new",
                                            "h_old_m", "h_new_m"], "rows": rows}}
    rep["pass"] = (worst <= TOL_DEG and worst_fine <= TOL_DEG and h_identical and not bad
                   and len(new_cache.h) == len(old_cache.h) and len(new_cache.fine) == len(old_cache.fine))
    return rep


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="re-key terrain.samples.json.gz for a heightfield grown by whole cells")
    ap.add_argument("project")
    ap.add_argument("--rows-n", type=int, required=True)
    ap.add_argument("--cols-w", type=int, required=True)
    ap.add_argument("--in", dest="src", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--in-place", action="store_true", help="allow --out to be the input cache")
    ap.add_argument("--proof", default=None, help="proof JSON (default: <out>.proof.json)")
    ap.add_argument("--samples", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=54)
    a = ap.parse_args(argv)
    proj = Path(a.project)
    if not proj.is_absolute():
        print("[remap] the project must be an ABSOLUTE path")
        return 2
    if a.rows_n < 0 or a.cols_w < 0 or (a.rows_n == 0 and a.cols_w == 0):
        print("[remap] --rows-n / --cols-w: whole cells >= 0, not both 0")
        return 2
    src = Path(a.src) if a.src else proj / "data" / ts.SAMPLES
    out = Path(a.out)
    if out.resolve() == src.resolve() and not a.in_place:
        print("[remap] --out is the input cache: pass --in-place to overwrite it on purpose")
        return 2
    tmp = out.with_name(out.name + ".tmp") if out.resolve() == src.resolve() else out
    rep = remap(proj, a.rows_n, a.cols_w, src, tmp, a.samples, a.seed)
    proof = Path(a.proof) if a.proof else out.with_name(out.name + ".proof.json")
    proof.write_text(json.dumps(rep, indent=1), encoding="utf-8")
    if rep["pass"] and tmp != out:
        tmp.replace(out)
    elif not rep["pass"]:
        tmp.unlink(missing_ok=True)                       # a re-keyed cache that fails its proof is never left behind
    print(f"[remap] {rep['keys']} keys + {rep['fine_keys']} fine keys shifted by {rep['key_shift_base']} (fine "
          f"{rep['key_shift_fine']}); max position change {rep['max_position_diff_deg_all_keys']:.3g} deg (all keys), "
          f"{rep['max_position_diff_deg_fine_keys']:.3g} deg (fine); h_cm byte-identical "
          f"{rep['h_cm_lists_byte_identical']}; {rep['random_nodes']} random nodes, "
          f"{len(rep['random_nodes_failing'])} failing -> {'PASS' if rep['pass'] else 'FAIL'} ({proof})")
    return 0 if rep["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())

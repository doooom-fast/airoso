"""Phase 3 Step 0.5: re-key data/terrain.samples.json.gz from the 26-column frame to the 88-column frame.

tools/remap_sample_cache.py does one growth from the installed (ungrown) frame and refuses a grown meta; the cache
today is already on the 26-column frame (its own remap record, key shift [+416, -592]). This applies the same
re-keying for the second growth, from the 26-column pin to the 88-column pin, with the tool's own proof: every key's
lon/lat in the old frame vs the new frame + shifted key within TOL_DEG (1e-9 deg), the h_cm lists byte-identical,
the file loading through terrain_sample.SampleCache under the new frame, 1,000 random nodes re-read through both.
Total shift from the installed frame = the plan's +1,408 base units (88 x 16).

    python -I p3_remap.py <airoso> <proj26> <proj88> <out.json.gz> <proof.json>
proj26 / proj88: project dirs whose track.config.json + data/heightfield.meta.json are the 26 / 88 column ones.
"""
import gzip
import json
import random
import sys
import time
from pathlib import Path

TOL_DEG = 1e-9


def main():
    airoso, p26, p88, out, proof_p = (Path(a) for a in sys.argv[1:6])
    sys.path.insert(0, str(airoso))
    from scripts.elevation import terrain_sample as ts
    from scripts.geometry import terrain_tiers as tt

    def frame_of(proj):
        cfg = json.loads((proj / "track.config.json").read_text())
        _l, origin, _f = ts.road_inputs(proj)
        spec = tt.TierSpec(cfg["terrain"], origin, bool(cfg.get("mirror_x", False)))
        return spec, spec.frame(tt.load_heightfield_meta(proj)), spec.frame_cfg.get("pin")

    s26, old, pin26 = frame_of(p26)
    s88, new, pin88 = frame_of(p88)
    up = int(s26.frame_cfg.get("upsample", 1))
    per = int(round(float(tt.load_heightfield_meta(p26)['spacing_m']) / max(1, up) / s26.base_m))
    k26 = tt.pin_key_shift(pin26, up, per)
    k88 = tt.pin_key_shift(pin88, up, per)
    kx, kz = k88[0] - k26[0], k88[1] - k26[1]
    src = p26 / "data" / ts.SAMPLES
    old_cache = ts.SampleCache(src, s26, old)
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
        "tool": "p3_remap.py (Lake Murray round 2 data run; tools/remap_sample_cache.py's re-keying and proof, "
                "second growth)",
        "why": "EXPANSION-PHASE3-PLAN Step 0.5: terrain.grid_grow.cols_w 26 -> 88, tier_options.frame.pin to match",
        "rows_n": pin88["rows_n"], "cols_w": pin88["cols_w"], "key_shift_base": [kx, -kz],
        "key_shift_fine": [kx * F, -kz * F], "from_lattice_frame": old.to_json(), "pin": pin88})
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(gzip.compress(json.dumps(nd, separators=(",", ":")).encode("utf-8"), 9, mtime=0))
    new_cache = ts.SampleCache(out, s88, new)
    ll = s26.to_lonlat

    def pos(f, i, j, q=1.0):
        return ll(f.x0 + i / q * f.ux, f.z0 + j / q * f.uz)

    worst = max(max(abs(a[0] - b[0]), abs(a[1] - b[1])) for a, b in
                ((pos(old, i, j), pos(new, i + kx, j - kz)) for i, j in zip(d["I"], d["J"])))
    worst_f = 0.0
    if d.get("fine"):
        worst_f = max(max(abs(a[0] - b[0]), abs(a[1] - b[1])) for a, b in
                      ((pos(old, i, j, float(F)), pos(new, i + kx * F, j - kz * F, float(F)))
                       for i, j in zip(d["fine"]["I"], d["fine"]["J"])))
    rng = random.Random(54)
    pick = rng.sample(sorted(old_cache.h), 1000)
    bad = [k for k in pick if new_cache.h.get((k[0] + kx, k[1] - kz)) != old_cache.h[k]
           or max(abs(a - b) for a, b in zip(pos(old, *k), pos(new, k[0] + kx, k[1] - kz))) > TOL_DEG]
    same_h = nd["h_cm"] == d["h_cm"] and (not d.get("fine") or nd["fine"]["h_cm"] == d["fine"]["h_cm"])
    rep = {"from_frame": old.to_json(), "to_frame": new.to_json(), "pin26": pin26, "pin88": pin88,
           "key_shift_base_from_26": [kx, -kz], "key_shift_base_from_installed": [k88[0], -k88[1]],
           "keys": len(d["I"]), "fine_keys": len((d.get("fine") or {}).get("I", [])),
           "max_position_diff_deg_all_keys": worst, "max_position_diff_deg_fine_keys": worst_f, "tol_deg": TOL_DEG,
           "h_cm_lists_byte_identical": same_h, "random_nodes": len(pick), "random_nodes_failing": bad,
           "loads_under_new_frame": len(new_cache.h) == len(old_cache.h) and len(new_cache.fine) == len(old_cache.fine)}
    rep["pass"] = worst <= TOL_DEG and worst_f <= TOL_DEG and same_h and not bad and rep["loads_under_new_frame"]
    proof_p.write_text(json.dumps(rep, indent=1))
    print(json.dumps({k: v for k, v in rep.items() if k != "random_nodes_failing"}), flush=True)
    if not rep["pass"]:
        out.unlink()
        raise SystemExit("remap proof FAILED")


if __name__ == "__main__":
    main()

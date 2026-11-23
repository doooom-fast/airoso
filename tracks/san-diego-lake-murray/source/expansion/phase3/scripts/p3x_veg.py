"""Phase 3 aerial lens: vegetation bins (the shape of source/expansion/aerial__veg_bins.json, read by
tools/make_treefx.py scenery.treefx.veg_bins: per piece, per 250 m bin, per side L / R of the clockwise direction,
[other, canopy, water, scrub] NAIP pixels of the 10-40 m band).

Sampling: every STEP_M along the line, offsets OFF_FROM..OFF_TO every OFF_STEP_M each side (2,000 samples a full
bin a side, as the Phase 2 file's full bins), nearest NAIP pixel through tools/naip_carriageways.Mosaic (cache only,
NAIP_OFFLINE=1). Classes from NAIP CIR (R G B NIR), NDVI = (NIR - R) / (NIR + R), brightness = mean(R, G, B):
  water   NDVI < WATER_NDVI and NIR < WATER_NIR
  canopy  NDVI >= CANOPY_NDVI and brightness < CANOPY_BRIGHT  (tree crowns: green and dark)
  scrub   NDVI >= SCRUB_NDVI, not canopy
  other   the rest (pavement, roofs, bare ground, dry grass)
The four thresholds are [invented]. `calibrate` picks them on the Phase 2 legs (A-D, routes__routes_analysis.json
fwd) against the Phase 2 file's own counts (its classifier's thresholds are invented too and were not kept), so the
two phases zone their trees by one rule.

    python -I p3x_veg.py calibrate <airoso> <naip-cache> <routes__routes_analysis.json> <aerial__veg_bins.json> <out.json>
    python -I p3x_veg.py bins <airoso> <naip-cache> <skeleton.west.json> <calibration.json> <out.json>
"""
import itertools
import json
import os
import sys
from pathlib import Path

os.environ["NAIP_OFFLINE"] = "1"
STEP_M = 5.0
OFF_FROM, OFF_TO, OFF_STEP_M = 10.0, 40.0, 0.75
BIN_M = 250.0


def samples(ae, np, mos, P):
    """per sample: (bin, side, R, G, B, N) along polyline P (local x, z)"""
    sl = ae.arc(P)
    offs = np.arange(OFF_FROM, OFF_TO - 1e-9, OFF_STEP_M)
    xs, zs, bins, sides = [], [], [], []
    k = 0
    while k * STEP_M <= sl[-1] + 1e-9:
        s = k * STEP_M
        a = ae.at_arc(P, sl, max(0.0, s - 1.0))
        b = ae.at_arc(P, sl, min(sl[-1], s + 1.0))
        c = ae.at_arc(P, sl, s)
        tx, tz = b[0] - a[0], b[1] - a[1]
        L = (tx * tx + tz * tz) ** 0.5 or 1.0
        nx, nz = -tz / L, tx / L
        for side, sg in (("L", 1.0), ("R", -1.0)):
            for o in offs:
                xs.append(c[0] + sg * o * nx)
                zs.append(c[1] + sg * o * nz)
                bins.append(int(s // BIN_M))
                sides.append(side)
        k += 1
    px = mos.sample(np.array(xs), np.array(zs))
    return np.array(bins), np.array(sides), px


def classify(np, px, t):
    r, g, b, n = px[:, 0], px[:, 1], px[:, 2], px[:, 3]
    ndvi = (n - r) / np.maximum(1.0, n + r)
    br = (r + g + b) / 3.0
    cls = np.zeros(len(px), np.int8)                                  # 0 other
    cls[(ndvi >= t["SCRUB_NDVI"])] = 3                                # scrub
    cls[(ndvi >= t["CANOPY_NDVI"]) & (br < t["CANOPY_BRIGHT"])] = 1   # canopy
    cls[(ndvi < t["WATER_NDVI"]) & (n < t["WATER_NIR"])] = 2          # water
    cls[np.isnan(r)] = -1
    return cls


def counts(np, bins, sides, cls):
    out = {}
    for bi in sorted(set(bins.tolist())):
        for side in ("L", "R"):
            m = (bins == bi) & (sides == side) & (cls >= 0)
            c = [int(((cls == k) & m).sum()) for k in (0, 1, 2, 3)]
            out[f"{bi}{side}"] = c
    return out


def main():
    mode, airoso, cache = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    sys.path.insert(0, str(airoso / "tools"))
    sys.path.insert(0, str(airoso))
    import numpy as np
    import author_expansion as ae
    import naip_carriageways as nc
    cl = json.loads((airoso / "tracks/san-diego-lake-murray/data/centerline.local.json").read_text())
    fr = ae.Frame(cl["origin"])
    mos = nc.Mosaic(cl["origin"], cache)
    if mode == "calibrate":
        an = json.loads(Path(sys.argv[4]).read_text())
        ref = json.loads(Path(sys.argv[5]).read_text())
        legs = {"W": "A", "P": "B", "M": "C", "J": "D"}
        S = {}
        for lg in an["fwd"]:
            if lg["leg"] in legs:
                P = [fr.xz(*c[:2]) for c in lg["geom"]]
                S[legs[lg["leg"]]] = samples(ae, np, mos, P)
        grid = {"CANOPY_NDVI": [0.10, 0.15, 0.20, 0.25, 0.30, 0.35],
                "CANOPY_BRIGHT": [60, 75, 90, 105, 120, 140, 255],
                "SCRUB_NDVI": [0.02, 0.05, 0.08, 0.10, 0.12, 0.15],
                "WATER_NDVI": [-0.05], "WATER_NIR": [45]}
        best = None
        for vals in itertools.product(*grid.values()):
            t = dict(zip(grid.keys(), vals))
            if t["SCRUB_NDVI"] > t["CANOPY_NDVI"]:
                continue
            err, n = 0.0, 0
            for pid, (bins, sides, px) in S.items():
                c = counts(np, bins, sides, classify(np, px, t))
                for key, rc in ref[pid].items():
                    mc = c.get(key)
                    if not mc or sum(rc) < 500 or sum(mc) < 500:
                        continue
                    rs = [v / sum(rc) for v in rc]
                    ms = [v / sum(mc) for v in mc]
                    err += abs(rs[1] - ms[1]) + abs(rs[3] - ms[3])
                    n += 1
            if n and (best is None or err / n < best[0]):
                best = (err / n, t, n)
        t = best[1]
        rep = {"thresholds": t, "mean_abs_share_error_canopy_plus_scrub": round(best[0], 4), "bins_compared": best[2],
               "grid": grid, "missing_tiles": mos.missing, "per_bin": {}}
        for pid, (bins, sides, px) in S.items():
            c = counts(np, bins, sides, classify(np, px, t))
            rep["per_bin"][pid] = {k: {"phase2": ref[pid].get(k), "this": c.get(k)} for k in ref[pid]}
        Path(sys.argv[6]).write_text(json.dumps(rep, indent=1))
        print("best", json.dumps(t), "err", round(best[0], 4), "bins", best[2], "missing", len(mos.missing))
    else:
        sk = json.loads(Path(sys.argv[4]).read_text())
        cal = json.loads(Path(sys.argv[5]).read_text())
        t = cal["thresholds"]
        names = {"E": "P3-WAR", "F": "P3-ZION", "G": "P3-MG"}
        out = {}
        for lid, pc in sk["pieces"].items():
            P = [(r[1], r[2]) for r in pc["stations"]]
            bins, sides, px = samples(ae, np, mos, P)
            out[names[lid]] = counts(np, bins, sides, classify(np, px, t))
        Path(sys.argv[6]).write_text(json.dumps(out, indent=1))
        for pid, c in out.items():
            sh = {k: (round(v[1] / max(1, sum(v)), 2), round(v[3] / max(1, sum(v)), 2)) for k, v in c.items()}
            print(pid, sh)
        print("missing tiles", mos.missing)


if __name__ == "__main__":
    main()

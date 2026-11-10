"""Per inventory line: non-ground returns within +-W of the line per height band, per metre of line, against the same
band in two control strips 3-6 m either side (scaled to the same width). python -I sumitems.py pts.npz hag.npz inventory.json [W] [out.json]"""
import json, sys, os
import numpy as np
os.environ.setdefault("REACH", "7")
_argv = sys.argv; sys.argv = [_argv[0], _argv[1], _argv[3], "-"]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import probe2  # noqa: E402
sys.argv = _argv
hag = np.load(sys.argv[2])["hag"]; inv = json.load(open(sys.argv[3])); W = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
e, n, cls = probe2.e, probe2.n, probe2.cls
out = {}
for it in inv["items"]:
    if "polyline_lonlat" not in it:
        continue
    poly = probe2.local(it["polyline_lonlat"])
    c0 = poly.mean(0); r = np.max(np.hypot(*(poly - c0).T)) + 8
    ids = np.array(probe2.T.query_ball_point(c0, r=r))
    if not len(ids):
        out[it["id"]] = "no returns (outside the 45 m read)"; continue
    al, off, L = probe2.frame(poly, np.c_[e[ids], n[ids]])
    ok = (al > 0.5) & (al < L - 0.5) & ~np.isin(cls[ids], (7, 18)) & np.isfinite(hag[ids])
    ids, al, off = ids[ok], al[ok], off[ok]
    h = hag[ids]; ng = cls[ids] != 2
    on = np.abs(off) <= W; ctl = (np.abs(off) >= 3) & (np.abs(off) <= 6)
    covered = len(np.unique((al[on & ~ng | on] // 1).astype(int)))
    row = {"len_m": round(L, 1), "metres_with_returns": int(covered), "ground_per_m2_on_line": round(float(((~ng) & on).sum() / (2 * W * L)), 2)}
    for a, b in ((0.35, 0.6), (0.6, 1.0), (1.0, 1.6), (1.6, 3.0), (3.0, 6.0)):
        row[f"{a}-{b} on/ctl per m"] = [round(float((ng & on & (h >= a) & (h < b)).sum() / L), 2),
                                        round(float((ng & ctl & (h >= a) & (h < b)).sum() / L * (2 * W) / 6), 2)]
    out[it["id"]] = row
for k, v in out.items():
    print(k, v)
if len(sys.argv) > 5:
    json.dump(out, open(sys.argv[5], "w"), indent=1)

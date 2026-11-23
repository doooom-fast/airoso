"""The blue / yellow stripe at R s 2,673 re-traced onto its paint (ledger 0081 "Owed (start here)"; ledger 0097 round 2).

    python -I retrace_stripe_2673.py <repo>      (numpy + Pillow; writes kerbs.lm.json beside itself)

Ledger 0081 round 3 left it: "R s 2,673-2,681's first ~8 m are built at the run's median offset while the paint lies 1.5-3 m
further out" (the stripe follows the corner of the link road's mouth, so one in / out cannot place it). The build lays each
run at in_m .. out_m across its live edge (edge_lonlat, tools/kerb_section.py), so the run is re-traced by moving each edge
point across by the paint it stands on: at every edge point of the run the 0.3 m crop (source/road_wear/naip_2023_030_hp.png)
is read every 0.1 m from 4 m inside to 6 m outside the edge, the paint (white: mean >= 150 and B >= 0.8 R; yellow: R >= 150,
(R + G) / 2 - B >= 30, mean >= 140; blue: B - (R + G) / 2 >= 12) found, and where the paint's centre lies more than MOVE_MIN_M
off the run's band centre ((in_m + out_m) / 2) the point moves outward by the difference. in_m / out_m, the ends and every
other run are kept. Writes the port's own kerbs.lm.json (route.kerbs_file; tracks/high-plains' kerbs.json is untouched).
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

MOVE_MIN_M = 0.3        # [invented] a paint centre this close to the band's centre is the band (the 0.3 m pixel)
RUN = ("right", 2673.0)


def mpd(lat0):
    phi = math.radians(lat0)
    return (111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi),
            111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi))


def retrace(repo: Path):
    T = repo / "tracks" / "high-plains-lm"
    src = json.loads((repo / "tracks" / "high-plains" / "source" / "edges" / "kerbs.json").read_text(encoding="utf-8"))
    meta = json.loads((T / "source" / "road_wear" / "naip_2023_030_hp.json").read_text(encoding="utf-8"))
    A = np.asarray(Image.open(T / "source" / "road_wear" / "naip_2023_030_hp.png").convert("RGB")).astype(np.float32)
    W, N, E, S = meta["corners"]
    h, w, _ = A.shape
    run = next(k for k in src["kerbs"] if k["side"] == RUN[0] and k["s0"] == RUN[1])
    lat0 = run["edge_lonlat"][0][1]
    mlon, mlat = mpd(lat0)
    pts = [((lo - W) * mlon, (la - S) * mlat) for lo, la in run["edge_lonlat"]]

    def rgb(x, z):
        lon = W + x / mlon; lat = S + z / mlat
        px = (lon - W) / (E - W) * w - 0.5; py = (N - lat) / (N - S) * h - 0.5
        x0 = np.clip(np.floor(px).astype(int), 0, w - 2); y0 = np.clip(np.floor(py).astype(int), 0, h - 2)
        tx = (px - x0)[..., None]; ty = (py - y0)[..., None]
        return (A[y0, x0] * (1 - tx) + A[y0, x0 + 1] * tx) * (1 - ty) + (A[y0 + 1, x0] * (1 - tx) + A[y0 + 1, x0 + 1] * tx) * ty
    offs = np.arange(-4.0, 6.0 + 1e-9, 0.1)
    centre = (run["in_m"] + run["out_m"]) / 2.0
    sg = -1.0 if run["side"] == "right" else 1.0
    new, rows = [], []
    for k, q in enumerate(pts):
        a, b = pts[max(k - 1, 0)], pts[min(k + 1, len(pts) - 1)]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        tx, tz = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        ox, oz = -tz * sg, tx * sg                                   # outward
        V = rgb(q[0] + ox * offs, q[1] + oz * offs)
        R, G, B = V[:, 0], V[:, 1], V[:, 2]
        mean = V.mean(1); yb = (R + G) / 2 - B
        paint = ((mean >= 150) & (B >= 0.8 * R)) | ((R >= 150) & (yb >= 30) & (mean >= 140)) | (B - (R + G) / 2 >= 12)
        idx = np.nonzero(paint)[0]
        if len(idx) < 3:
            new.append(q); rows.append({"v": k, "paint_m": None, "moved_m": 0.0}); continue
        # the paint band nearest the run's band (the first contiguous band from the inside)
        j0 = idx[0]; j1 = j0
        while j1 + 1 < len(offs) and paint[j1 + 1]:
            j1 += 1
        c = (offs[j0] + offs[j1]) / 2.0
        d = c - centre
        mv = d if abs(d) > MOVE_MIN_M else 0.0
        new.append((q[0] + ox * mv, q[1] + oz * mv))
        rows.append({"v": k, "paint_m": [round(float(offs[j0]), 2), round(float(offs[j1]), 2)], "moved_m": round(float(mv), 2)})
    run2 = dict(run)
    run2["edge_lonlat"] = [[round(W + x / mlon, 8), round(S + z / mlat, 8)] for x, z in new]
    run2["edge_lonlat_was"] = run["edge_lonlat"]
    run2["_retrace"] = ("ledger 0097 round 2: each edge point moved outward by its paint's centre less the band's "
                        f"({centre:+.2f} m), where that is over {MOVE_MIN_M} m (retrace_stripe_2673.py, NAIP 2023 0.3 m); per point: "
                        + "; ".join(f"v{r['v']} paint {r['paint_m']} moved {r['moved_m']:+.2f}" for r in rows))
    out = dict(src)
    out["kerbs"] = [run2 if k is run else k for k in src["kerbs"]]
    out["_doc_lm"] = ("High Plains' port copy of tracks/high-plains/source/edges/kerbs.json (route.kerbs_file, synced in by "
                      "ship.json): the same 20 runs, R s 2,673 re-traced onto its paint (retrace_stripe_2673.py; ledger 0097 "
                      "round 2)")
    return out, rows


if __name__ == "__main__":
    repo = Path(sys.argv[1]).resolve()
    out, rows = retrace(repo)
    (Path(__file__).resolve().parent / "kerbs.lm.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for r in rows:
        print(r)

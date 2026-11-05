"""Find racing kerbs by their alternating blocks, whatever their faded colour (ledger 0081).

A painted kerb alternates light and colour blocks ALONG the edge (~1 m each). NAIP's faded reds read pink or grey, so a
colour reader misses most of a run (Pueblo at 0.3 m: tools/aerial_edges.py found 57 m where the zooms show hundreds). This
reads the luminance along the track's own lane edges (data/gate_centerline.json, its widths) every SAMPLE_M, in columns
OFF_STEP_M apart across the band OFF_LO_M..OFF_HI_M past the edge, and in a WIN_M window asks how strongly each column
alternates at a period between PERIOD_M (the strongest fitted sine, detrended). A station side is kerb where some column's
amplitude reaches MIN_AMP and its mean is light (MIN_MEAN: blocks on a bright paint, not cracks in asphalt); runs shorter
than MIN_RUN_M are dropped and gaps up to GAP_M joined. Every number is [invented] tuning (GATES-CHANGELOG 2026-11-05); the
runs it prints are CANDIDATES, each to be checked by eye on tools/edge_sheet.py zooms before tools/kerb_spans.py measures it.

    python tools/kerb_blocks.py <track-dir> --image <png> --corners W,N,E,S [--out <json>]
"""
from __future__ import annotations

import bisect
import json
import math
import sys
from pathlib import Path

from PIL import Image

SAMPLE_M = 0.25
OFF_LO_M, OFF_HI_M, OFF_STEP_M = -2.0, 1.5, 0.15
WIN_M = 6.0
PERIOD_M = (1.5, 1.75, 2.0, 2.25, 2.5)
MIN_AMP = 22.0
MIN_MEAN = 125.0
MIN_RUN_M = 5.0
GAP_M = 4.0


def mpd(lat0):
    phi = math.radians(lat0)
    return (111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi),
            111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    tdir = Path(argv.pop(0))
    opt = {}
    while argv:
        k = argv.pop(0)
        opt[k] = argv.pop(0)
    img = Image.open(opt["--image"]).convert("L")
    W_, H_ = img.size
    pix = img.load()
    cw, cn, ce, cs = (float(v) for v in opt["--corners"].split(","))
    local = json.loads((tdir / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    lon0, lat0 = float(local["origin"]["lon"]), float(local["origin"]["lat"])
    m_lon, m_lat = mpd(lat0)
    line = json.loads((tdir / "data" / "gate_centerline.json").read_text(encoding="utf-8"))
    P, Wd = line["points_xyz_m"], line["widths_m"]
    st = [0.0]
    for a, b in zip(P, P[1:]):
        st.append(st[-1] + math.hypot(b[0] - a[0], b[2] - a[2]))

    def at(s):
        j = min(len(P) - 2, max(0, bisect.bisect_right(st, s) - 1))
        t = (s - st[j]) / ((st[j + 1] - st[j]) or 1.0)
        x = P[j][0] + (P[j + 1][0] - P[j][0]) * t
        n = P[j][2] + (P[j + 1][2] - P[j][2]) * t
        a, b = P[max(0, j - 1)], P[min(len(P) - 1, j + 2)]
        tx, tz = b[0] - a[0], b[2] - a[2]
        L = math.hypot(tx, tz) or 1.0
        return x, n, -tz / L, tx / L, (Wd[j] + (Wd[j + 1] - Wd[j]) * t) / 2.0

    offs = [OFF_LO_M + k * OFF_STEP_M for k in range(int((OFF_HI_M - OFF_LO_M) / OFF_STEP_M) + 1)]
    ns = int(st[-1] / SAMPLE_M)
    win = int(WIN_M / SAMPLE_M)
    out = {"_doc": __doc__.split("\n\n")[0], "params": {k: v for k, v in globals().items() if k.isupper()}, "runs": []}
    for side in (1, -1):
        grid = []                                          # [station][offset] luminance
        for i in range(ns):
            x, n, lx, lz, hw = at(i * SAMPLE_M)
            row = []
            for o in offs:
                d = side * (hw + o)
                lon, lat = lon0 + (x + lx * d) / m_lon, lat0 + (n + lz * d) / m_lat
                X, Y = int(round((lon - cw) / (ce - cw) * W_)), int(round((cn - lat) / (cn - cs) * H_))
                row.append(pix[X, Y] if 0 <= X < W_ and 0 <= Y < H_ else 0)
            grid.append(row)
        flag = [None] * ns                                 # (min off, max off) of alternating columns
        for i in range(ns - win):
            hits = []
            for c, o in enumerate(offs):
                v = [grid[i + k][c] for k in range(win)]
                mean = sum(v) / win
                if mean < MIN_MEAN:
                    continue
                slope = (v[-1] - v[0]) / (win - 1)
                r = [v[k] - mean - slope * (k - (win - 1) / 2) for k in range(win)]
                best = 0.0
                for per in PERIOD_M:
                    w = 2 * math.pi * SAMPLE_M / per
                    a = sum(r[k] * math.cos(w * k) for k in range(win))
                    b = sum(r[k] * math.sin(w * k) for k in range(win))
                    best = max(best, 2 * math.hypot(a, b) / win)
                if best >= MIN_AMP:
                    hits.append(o)
            if hits:
                flag[i + win // 2] = (min(hits), max(hits))
        i = 0
        while i < ns:
            if flag[i] is None:
                i += 1
                continue
            j, last = i, i
            while j + 1 < ns and (j + 1 - last) * SAMPLE_M <= GAP_M:
                j += 1
                if flag[j] is not None:
                    last = j
            seg = [f for f in flag[i:last + 1] if f]
            if (last - i) * SAMPLE_M >= MIN_RUN_M:
                ins = sorted(f[0] for f in seg)
                ous = sorted(f[1] for f in seg)
                out["runs"].append({"side": "left" if side == 1 else "right", "s0": round(i * SAMPLE_M, 1),
                                    "s1": round(last * SAMPLE_M, 1), "in_m": ins[len(ins) // 2], "out_m": ous[len(ous) // 2]})
            i = last + 1
    for r in out["runs"]:
        print(f"[kerb_blocks] {r['side'][0].upper()} s {r['s0']:7.1f}-{r['s1']:7.1f}  across {r['in_m']:+.2f}..{r['out_m']:+.2f} m")
    print(f"[kerb_blocks] {len(out['runs'])} candidate runs, {sum(r['s1'] - r['s0'] for r in out['runs']):.0f} m")
    if "--out" in opt:
        Path(opt["--out"]).write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()

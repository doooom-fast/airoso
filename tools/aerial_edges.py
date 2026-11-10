"""Racing kerbs and paved run-off traced off a georeferenced aerial along a circuit's line (ledger 0078; the
aerial-tracing approach: the image is the measurement, the line only says where to look).

At every STEP_M of the track's own swept line (data/gate_centerline.json: engine frame, its widths) and on both sides,
the aerial is read across the lane edge, every 0.25 m from 2 m inside the edge to SCAN_M outside it, and each pixel is
classed by colour:
  kerb paint  white (mean >= 160, max - min <= 50, not yellow: B >= R - 45) or a kerb colour (blue: B > R + 25 and B > G; red: R > G + 25 and R > B + 20)
  asphalt     dark and unsaturated (max < 125, max - min < 28)
  other       ground, dirt, grass, shadow
A KERB is a station side whose band within ±KERB_BAND_M of the lane edge holds, over ±KERB_WIN_M along the line, both
white and a kerb colour (the stripes alternate ALONG the kerb, so one cross-section sees one or the other; a white edge
line alone has no colour, a blue-and-white barrier stands further out than the band), its
lateral extent the first / last kerb-paint offset; runs shorter than MIN_KERB_M are dropped and gaps up to GAP_M joined.
PAVED RUN-OFF is the asphalt (or kerb paint) that continues past the lane edge without a break of BREAK_M: its width per
station side, median-filtered over 9 m, kept where it is at least MIN_RUNOFF_W_M for MIN_RUNOFF_M. Every number below is
[invented] tuning of a colour reader; what the image shows is the measurement, and the overview / corner crops written
beside the output are there to be checked by eye against it.

    python tools/aerial_edges.py <track-dir> --image <png|jpg> (--georef <z18 georef.json> | --corners W,N,E,S)
                                 --imagery "<source, date>" [--out <dir>]

Writes <out>/edges.traced.json (stations on the gate line, AND every run as lon/lat polylines so a line change does not
lose it) and <out>/edges_overview.png. Default out: <track-dir>/source/edges.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

STEP_M = 1.0
SCAN_M = 14.0
KERB_BAND_M = 2.5
KERB_WIN_M = 3.0
MIN_KERB_M = 5.0
GAP_M = 8.0
BREAK_M = 1.0
MIN_RUNOFF_W_M = 1.5
MIN_RUNOFF_M = 10.0


def mpd(lat0):
    phi = math.radians(lat0)
    return (111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi),
            111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi))


def classify(p):
    r, g, b = p[:3]
    mx, mn = max(r, g, b), min(r, g, b)
    if b > r + 25 and b > g:                       # the colours first: a light kerb blue is also bright
        return "blue"
    if r > g + 25 and r > b + 20:                  # NAIP's kerb reds are muted (a painted kerb reads ~ (190, 150, 140))
        return "red"
    if (r + g + b) / 3 >= 160 and mx - mn <= 50 and b >= r - 45:
        return "white"
    if mx < 125 and mx - mn < 28:
        return "asphalt"
    return "other"


def runs(flags, st, min_len, gap):
    out, a, last = [], None, None
    for i, f in enumerate(flags):
        if f:
            if a is None:
                a = i
            elif st[i] - st[last] > gap:
                out.append((a, last)); a = i
            last = i
    if a is not None:
        out.append((a, last))
    return [(a, b) for a, b in out if st[b] - st[a] >= min_len]


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    tdir = Path(argv.pop(0))
    opt = {}
    while argv:
        k = argv.pop(0); opt[k] = argv.pop(0)
    img = Image.open(opt["--image"]).convert("RGB")
    W_, H_ = img.size
    pix = img.load()
    local = json.loads((tdir / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    lon0, lat0 = float(local["origin"]["lon"]), float(local["origin"]["lat"])
    m_lon, m_lat = mpd(lat0)
    if "--georef" in opt:
        G = json.loads(Path(opt["--georef"]).read_text(encoding="utf-8"))
        z, gx0, gy0 = G["z"], G["x0"] * 256, G["y0"] * 256
        sx = W_ / G["w"] if G.get("w") else 1.0

        def to_px(lon, lat):
            n = 2 ** z * 256
            X = (lon + 180) / 360 * n
            Y = (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n
            return (X - gx0) * sx, (Y - gy0) * sx
        mpp = G["m_per_px_equator"] * math.cos(math.radians(lat0)) / sx
    else:
        cw, cn, ce, cs = (float(v) for v in opt["--corners"].split(","))

        def to_px(lon, lat):
            return (lon - cw) / (ce - cw) * W_, (cn - lat) / (cn - cs) * H_
        mpp = (ce - cw) * m_lon / W_

    def xy_px(x, zz):
        return to_px(lon0 + x / m_lon, lat0 + zz / m_lat)

    def sample(x, zz):
        X, Y = xy_px(x, zz)
        i, j = int(round(X)), int(round(Y))
        if 0 <= i < W_ and 0 <= j < H_:
            return pix[i, j]
        return None

    line = json.loads((tdir / "data" / "gate_centerline.json").read_text(encoding="utf-8"))
    P, Wd = line["points_xyz_m"], line["widths_m"]
    st = [0.0]
    for a, b in zip(P, P[1:]):
        st.append(st[-1] + math.hypot(b[0] - a[0], b[2] - a[2]))
    import bisect
    stations, nxt = [], 0.0
    while nxt <= st[-1]:
        j = min(len(P) - 2, max(0, bisect.bisect_right(st, nxt) - 1))
        t = (nxt - st[j]) / ((st[j + 1] - st[j]) or 1.0)
        x = P[j][0] + (P[j + 1][0] - P[j][0]) * t
        zz = P[j][2] + (P[j + 1][2] - P[j][2]) * t
        a, b = P[max(0, j - 1)], P[min(len(P) - 1, j + 2)]
        tx, tz = b[0] - a[0], b[2] - a[2]; L = math.hypot(tx, tz) or 1.0
        hw = (Wd[j] + (Wd[j + 1] - Wd[j]) * t) / 2.0
        stations.append((nxt, x, zz, -tz / L, tx / L, hw))
        nxt += STEP_M
    offs = [k * 0.25 for k in range(-8, int(SCAN_M / 0.25) + 1)]       # metres past the lane edge
    rec = {1: [], -1: []}
    for s, x, zz, lx, lz, hw in stations:
        for side in (1, -1):
            cls = []
            for o in offs:
                d = side * (hw + o)
                p = sample(x + lx * d, zz + lz * d)
                cls.append(None if p is None else classify(p))
            band = [c for o, c in zip(offs, cls) if abs(o) <= KERB_BAND_M and c]
            nb = len(band) or 1
            kin = [o for o, c in zip(offs, cls) if abs(o) <= KERB_BAND_M and c in ("white", "blue", "red")]
            w_ro, gap_m = 0.0, 0.0
            for o, c in zip(offs, cls):
                if o < 0:
                    continue
                if c in ("asphalt", "white", "blue", "red"):
                    w_ro, gap_m = o, 0.0
                else:
                    gap_m += 0.25
                    if gap_m >= BREAK_M:
                        break
            rec[side].append({"n": nb, "white": sum(c == "white" for c in band), "blue": sum(c == "blue" for c in band),
                              "red": sum(c == "red" for c in band), "kin": kin, "runoff_w": w_ro})
    ss = [s[0] for s in stations]
    out = {"_doc": __doc__.split("\n\n")[0], "tool": "tools/aerial_edges.py", "imagery": opt.get("--imagery"),
           "image": opt["--image"], "m_per_px": round(mpp, 3), "line": "data/gate_centerline.json (engine frame)",
           "origin": local["origin"], "params": {k: v for k, v in globals().items() if k.isupper()},
           "kerbs": [], "runoff": []}

    def lonlat(i, side, o):
        s, x, zz, lx, lz, hw = stations[i]
        d = side * (hw + o)
        return [round(lon0 + (x + lx * d) / m_lon, 8), round(lat0 + (zz + lz * d) / m_lat, 8)]
    hw_win = int(round(KERB_WIN_M / STEP_M))
    for side in (1, -1):
        R = rec[side]
        for i, r in enumerate(R):                       # the stripes alternate along the kerb: read a window of stations
            win = R[max(0, i - hw_win):i + hw_win + 1]
            n = sum(w["n"] for w in win) or 1
            wh, bl, rd = (sum(w[k] for w in win) / n for k in ("white", "blue", "red"))
            own = (r["white"] + r["blue"] + r["red"]) / (r["n"] or 1)
            r["kerb"] = wh >= 0.08 and (bl + rd) >= 0.08 and own >= 0.15
            r["colour"] = "blue" if bl >= rd else "red"
            r["k_in"] = min(r["kin"]) if r["kerb"] and r["kin"] else None
            r["k_out"] = max(r["kin"]) if r["kerb"] and r["kin"] else None
        for a, b in runs([r["kerb"] for r in R], ss, MIN_KERB_M, GAP_M):
            ks = [r for r in R[a:b + 1] if r["kerb"]]
            k_in = sorted(r["k_in"] for r in ks)[len(ks) // 2]
            k_out = sorted(r["k_out"] for r in ks)[len(ks) // 2]
            colour = max(("blue", "red"), key=lambda c: sum(r["colour"] == c for r in ks))
            out["kerbs"].append({"side": "left" if side == 1 else "right", "s0": ss[a], "s1": ss[b],
                                 "in_m": k_in, "out_m": k_out, "colour": colour,
                                 "edge_lonlat": [lonlat(i, side, 0.0) for i in range(a, b + 1, 2)]})
        wv = [r["runoff_w"] for r in R]
        med = [sorted(wv[max(0, i - 4):i + 5])[len(wv[max(0, i - 4):i + 5]) // 2] for i in range(len(wv))]
        for a, b in runs([m >= MIN_RUNOFF_W_M for m in med], ss, MIN_RUNOFF_M, 2.0):
            out["runoff"].append({"side": "left" if side == 1 else "right", "s0": ss[a], "s1": ss[b],
                                  "width_m": [round(med[i], 2) for i in range(a, b + 1)],
                                  "outline_lonlat": [lonlat(i, side, 0.0) for i in range(a, b + 1, 2)] +
                                                    [lonlat(i, side, med[i]) for i in range(b, a - 1, -2)]})
    od = Path(opt.get("--out") or (tdir / "source" / "edges"))
    od.mkdir(parents=True, exist_ok=True)
    (od / "edges.traced.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    # the overview, to check by eye: kerbs magenta, run-off outlines yellow, the lane edges cyan
    ov = img.copy(); d = ImageDraw.Draw(ov)
    for side in (1, -1):
        d.line([xy_px(s[1] + s[3] * side * s[5], s[2] + s[4] * side * s[5]) for s in stations], fill=(0, 255, 255), width=1)
    for ro in out["runoff"]:
        d.polygon([to_px(*q) for q in ro["outline_lonlat"]], outline=(255, 230, 0))
    for k in out["kerbs"]:
        d.line([to_px(*q) for q in k["edge_lonlat"]], fill=(255, 0, 255), width=4)
    ov.save(od / "edges_overview.png")
    print(f"[edges] {tdir.name}: {len(out['kerbs'])} kerb runs ({sum(k['s1'] - k['s0'] for k in out['kerbs']):.0f} m), "
          f"{len(out['runoff'])} paved run-off runs ({sum(r['s1'] - r['s0'] for r in out['runoff']):.0f} m) at "
          f"{mpp:.2f} m/px -> {od}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

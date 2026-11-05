"""Where a kerb's paint lies across the lane edge, read from its alternating blocks alone, colour not used (ledger 0081 round 3).

NAIP's faded kerb red reads pink or grey (Pueblo, Aspen, Nevada: tools/kerb_spans.py's red class finds 0 red pixels at
kerbs seen by eye), and the white reads like pale sand or the lot's concrete, so a colour reader cannot place them. What
every painted kerb still shows is its BLOCKS: light and dark alternating ALONG the edge, in phase across the kerb's width.
This reads that, and only that:

  1. the luminance on a grid along the track's own lane edge (data/gate_centerline.json, its widths): rows every DS_M
     along s, columns every DO_M across the edge from O_LO_M to O_HI_M (bilinear, pixel centres at +0.5);
  2. per station (every STEP_M over the span), a window WIN_M long: every column detrended (mean and slope); the
     REFERENCE waveform is the column whose detrended signal carries the most energy at a block period (PERIOD_M), then
     the mean of the columns in the band found from it (REFINE passes);
  3. each column's matched-filter coefficient on the reference (least squares: k = <col, ref> / <ref, ref>): ~1 where the
     column lies wholly on the blocks, ~0 where it never alternates (asphalt, dirt), between at the blurred paint edge;
  4. the band: the contiguous columns round the peak with k over HALF of the peak; its two crossings (linearly
     interpolated) are the paint's inner and outer edge at that station (a half-maximum of a blurred step is the step);
  5. a station counts when the reference's block amplitude (its strongest sine at PERIOD_M) is at least MIN_AMP;
     in_m / out_m = the median over counted stations (as tools/kerb_spans.py's are);
  6. the extent: the band's mean signal along s, its block amplitude in a window EXT_WIN_M long round each 0.25 m;
     the run continues outward from the eye span's counted stations while the amplitude stays over EXT_FRAC of the
     span's median, over gaps up to GAP_M, at most GROW_M past either eye end.

Calibrated against High Plains' 20 colour-measured runs (tools/kerb_spans.py on NAIP 2023 0.3 m, where blue reads as blue):
`--truth <kerbs.json>` prints each run's residual and the median / p95 / max (ledger 0081 round 3). Every number here is
[invented] tuning of a block reader (GATES-CHANGELOG 2026-11-05, round 3); the image is the measurement.

    python tools/kerb_offsets.py <track-dir> --image <png> --corners W,N,E,S --spans "L:212-239:red_white,..." \
           [--truth <kerbs.json>] [--out <json>] [--strips <jpg>] [--imagery "<what, when, resolution>"] [--how "<how>"]

--spans takes the eye-checked spans (side:s0-s1[:colour]); with --truth and no --spans, the truth file's own eye spans
(s_eye, else s0-s1) are read. --out writes a kerbs file in tools/kerb_spans.py's shape (route.kerbs_file).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

DS_M = 0.25
DO_M = 0.075
O_LO_M, O_HI_M = -3.5, 3.5
STEP_M = 1.0
WIN_M = 6.0
PERIOD_M = (1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 3.0)
REFINE = 2
HALF = 0.5
MIN_AMP = 8.0
EXT_WIN_M = 3.0
EXT_FRAC = 0.5
GAP_M = 3.0
GROW_M = 15.0
PROFILE = {"blue_white": "kerb", "red_white": "kerb", "blue_yellow": "paint"}


def mpd(lat0):
    phi = math.radians(lat0)
    return (111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi),
            111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi))


def detrend(v):
    """v: (rows, cols) -> each column less its mean and its linear trend along the rows"""
    n = v.shape[0]
    t = np.arange(n) - (n - 1) / 2.0
    v = v - v.mean(axis=0)
    slope = (t[:, None] * v).sum(axis=0) / max((t * t).sum(), 1e-9)
    return v - slope[None, :] * t[:, None]


def block_amp(v, periods=PERIOD_M):
    """v: (rows,) or (rows, cols) detrended -> the strongest fitted sine's amplitude at a block period (per column)"""
    n = v.shape[0]
    q = np.arange(n) * DS_M
    best = np.zeros(v.shape[1:]) if v.ndim > 1 else 0.0
    for per in periods:
        w = 2 * math.pi / per
        c, s = np.cos(w * q), np.sin(w * q)
        a = np.tensordot(c, v, axes=(0, 0))
        b = np.tensordot(s, v, axes=(0, 0))
        best = np.maximum(best, 2 * np.hypot(a, b) / n)
    return best


def crossings(k, offs, half=HALF):
    """the band round k's peak where k > half * peak -> (inner, outer) offsets, linearly interpolated"""
    c = int(np.argmax(k))
    pk = k[c]
    if pk <= 0:
        return None
    thr = half * pk
    lo = c
    while lo > 0 and k[lo - 1] > thr:
        lo -= 1
    hi = c
    while hi < len(k) - 1 and k[hi + 1] > thr:
        hi += 1
    if lo == 0 or hi == len(k) - 1:
        return None                                        # the band runs off the grid: no edge seen
    o_in = offs[lo - 1] + (thr - k[lo - 1]) / (k[lo] - k[lo - 1]) * (offs[lo] - offs[lo - 1])
    o_out = offs[hi] + (k[hi] - thr) / (k[hi] - k[hi + 1]) * (offs[hi + 1] - offs[hi])
    return o_in, o_out, lo, hi


class Edge:
    def __init__(self, tdir, image, corners):
        rgb = Image.open(image).convert("RGB")
        self.rgb = np.asarray(rgb, dtype=np.float64)
        img = np.asarray(rgb.convert("L"), dtype=np.float64)
        self.img = img
        self.H, self.W = img.shape
        self.cw, self.cn, self.ce, self.cs = corners
        local = json.loads((Path(tdir) / "data" / "centerline.local.json").read_text(encoding="utf-8"))
        self.lon0, self.lat0 = float(local["origin"]["lon"]), float(local["origin"]["lat"])
        self.m_lon, self.m_lat = mpd(self.lat0)
        line = json.loads((Path(tdir) / "data" / "gate_centerline.json").read_text(encoding="utf-8"))
        self.P = np.asarray(line["points_xyz_m"], dtype=np.float64)
        self.Wd = np.asarray(line["widths_m"], dtype=np.float64)
        d = np.hypot(np.diff(self.P[:, 0]), np.diff(self.P[:, 2]))
        self.st = np.concatenate([[0.0], np.cumsum(d)])

    def at(self, s):
        """s (array) -> x, n, left normal (lx, lz), half width; as tools/kerb_spans.py's at()"""
        P, st = self.P, self.st
        s = np.clip(s, 0.0, st[-1])
        j = np.clip(np.searchsorted(st, s, side="right") - 1, 0, len(P) - 2)
        t = (s - st[j]) / np.where(st[j + 1] - st[j] > 0, st[j + 1] - st[j], 1.0)
        x = P[j, 0] + (P[j + 1, 0] - P[j, 0]) * t
        n = P[j, 2] + (P[j + 1, 2] - P[j, 2]) * t
        a, b = P[np.maximum(0, j - 1)], P[np.minimum(len(P) - 1, j + 2)]
        tx, tz = b[:, 0] - a[:, 0], b[:, 2] - a[:, 2]
        L = np.hypot(tx, tz)
        L = np.where(L > 0, L, 1.0)
        return x, n, -tz / L, tx / L, (self.Wd[j] + (self.Wd[j + 1] - self.Wd[j]) * t) / 2.0

    def lonlat(self, s, side, o):
        x, n, lx, lz, hw = self.at(np.atleast_1d(np.asarray(s, dtype=np.float64)))
        d = side * (hw[:, None] + np.atleast_1d(o)[None, :])
        return (self.lon0 + (x[:, None] + lx[:, None] * d) / self.m_lon,
                self.lat0 + (n[:, None] + lz[:, None] * d) / self.m_lat)

    def grid(self, s, side, offs, rgb=False):
        """luminance (len(s), len(offs)), bilinear; NaN off the image (rgb: (len(s), len(offs), 3))"""
        lon, lat = self.lonlat(s, side, offs)
        X = (lon - self.cw) / (self.ce - self.cw) * self.W - 0.5
        Y = (self.cn - lat) / (self.cn - self.cs) * self.H - 0.5
        x0, y0 = np.floor(X).astype(int), np.floor(Y).astype(int)
        ok = (x0 >= 0) & (y0 >= 0) & (x0 < self.W - 1) & (y0 < self.H - 1)
        x0c, y0c = np.clip(x0, 0, self.W - 2), np.clip(y0, 0, self.H - 2)
        fx, fy = X - x0, Y - y0
        if rgb:
            I = self.rgb
            fx, fy, ok = fx[..., None], fy[..., None], ok[..., None]
        else:
            I = self.img
        v = (I[y0c, x0c] * (1 - fx) * (1 - fy) + I[y0c, x0c + 1] * fx * (1 - fy)
             + I[y0c + 1, x0c] * (1 - fx) * fy + I[y0c + 1, x0c + 1] * fx * fy)
        return np.where(ok, v, np.nan)


def strips(E, rows, path, px_per_m=12, pad_m=8.0):
    """a sheet of straightened strips, one per run: s left to right, offset across (outward = up), the aerial resampled
    on the line's own frame; lane edge cyan, the reader's in / out and extent yellow, a truth's in / out magenta"""
    from PIL import ImageDraw
    offs = np.arange(O_HI_M, O_LO_M - 1e-9, -1.0 / px_per_m)
    tiles = []
    for side, m, label, tr in rows:
        ss = np.arange(m["s0"] - pad_m, m["s1"] + pad_m + 1e-9, 1.0 / px_per_m)
        G = E.grid(ss, side, offs, rgb=True)
        im = Image.fromarray(np.nan_to_num(G, nan=0.0).clip(0, 255).astype(np.uint8).transpose(1, 0, 2))
        d = ImageDraw.Draw(im)
        y = lambda o: (O_HI_M - o) * px_per_m  # noqa: E731
        x = lambda s: (s - ss[0]) * px_per_m  # noqa: E731
        d.line([(0, y(0)), (im.width, y(0))], fill=(0, 220, 255), width=1)
        for o in (m["in_m"], m["out_m"]):
            for x0 in range(0, im.width, 8):
                d.line([(x0, y(o)), (x0 + 4, y(o))], fill=(255, 230, 0), width=1)
        for s in (m["s0"], m["s1"]):
            d.line([(x(s), 0), (x(s), im.height)], fill=(255, 230, 0), width=1)
        if tr:
            for o in (tr["in_m"], tr["out_m"]):
                for x0 in range(4, im.width, 8):
                    d.line([(x0, y(o)), (x0 + 4, y(o))], fill=(255, 0, 255), width=1)
            for s in (tr["s0"], tr["s1"]):
                for y0 in range(0, im.height, 8):
                    d.line([(x(s), y0), (x(s), y0 + 4)], fill=(255, 0, 255), width=1)
        for k in range(int(ss[0] // 10 + 1) * 10, int(ss[-1]) + 1, 10):
            d.line([(x(k), im.height - 6), (x(k), im.height)], fill=(255, 255, 255), width=1)
        lab = Image.new("RGB", (im.width, 14), (0, 0, 0))
        ImageDraw.Draw(lab).text((2, 1), label, fill=(255, 255, 255))
        t = Image.new("RGB", (im.width, im.height + 14))
        t.paste(lab, (0, 0))
        t.paste(im, (0, 14))
        tiles.append(t)
    sheet = Image.new("RGB", (max(t.width for t in tiles), sum(t.height + 4 for t in tiles)), (40, 40, 40))
    yy = 0
    for t in tiles:
        sheet.paste(t, (0, yy))
        yy += t.height + 4
    sheet.save(path, quality=92)


def station(G, offs):
    """G: (rows, cols) luminance in one window -> (in, out, amp, k) or None"""
    if np.isnan(G).any():
        return None
    D = detrend(G)
    amp = block_amp(D)
    c = int(np.argmax(amp))
    ref = D[:, c]
    band = None
    for _ in range(REFINE + 1):
        rr = float((ref * ref).sum())
        if rr <= 0:
            return None
        k = (D * ref[:, None]).sum(axis=0) / rr
        band = crossings(k, offs)
        if band is None:
            return None
        lo, hi = band[2], band[3]
        ref = D[:, lo:hi + 1].mean(axis=1)
    a = float(block_amp(ref))
    return band[0], band[1], a, k


def measure(E, side, s0, s1):
    offs = np.arange(O_LO_M, O_HI_M + 1e-9, DO_M)
    half = int(round(WIN_M / 2 / DS_M))
    lo_s, hi_s = s0 - GROW_M - WIN_M, s1 + GROW_M + WIN_M
    ss = np.arange(lo_s, hi_s + 1e-9, DS_M)
    G = E.grid(ss, side, offs)
    rows = []
    s = s0
    while s <= s1 + 1e-6:
        i = int(round((s - lo_s) / DS_M))
        r = station(G[i - half:i + half + 1], offs)
        if r is not None and r[2] >= MIN_AMP:
            rows.append((s, r[0], r[1], r[2]))
        s += STEP_M
    if not rows:
        return None
    ins = sorted(r[1] for r in rows)
    outs = sorted(r[2] for r in rows)
    o_in, o_out = ins[len(ins) // 2], outs[len(outs) // 2]
    # the extent: the band's mean signal along s, its block amplitude in an EXT_WIN_M window round each row; walked out
    # from the span's own over-threshold rows while it stays over EXT_FRAC of the span's median (gaps up to GAP_M)
    amp_med = float(np.median([r[3] for r in rows]))
    cols = (offs >= o_in) & (offs <= o_out)
    if not cols.any():
        cols = np.abs(offs - (o_in + o_out) / 2) <= DO_M
    b = np.nanmean(G[:, cols], axis=1)
    hw = int(round(EXT_WIN_M / 2 / DS_M))
    a = np.zeros(len(ss))
    for i in range(hw, len(ss) - hw):
        v = b[i - hw:i + hw + 1]
        if not np.isnan(v).any():
            a[i] = block_amp(detrend(v[:, None]))[0]
    i0, i1 = int(round((s0 - lo_s) / DS_M)), int(round((s1 - lo_s) / DS_M))
    ok = a >= EXT_FRAC * float(np.median(a[i0:i1 + 1]))
    inside = np.where(ok[i0:i1 + 1])[0] + i0
    if not len(inside):
        return None
    gap = int(round(GAP_M / DS_M))
    g0, g1 = int(round((s0 - GROW_M - lo_s) / DS_M)), int(round((s1 + GROW_M - lo_s) / DS_M))
    lo, hi = int(inside[0]), int(inside[-1])
    while True:
        nxt = [q for q in range(lo - 1, max(g0, lo - gap) - 1, -1) if ok[q]]
        if not nxt:
            break
        lo = nxt[0]
    while True:
        nxt = [q for q in range(hi + 1, min(g1, hi + gap) + 1) if ok[q]]
        if not nxt:
            break
        hi = nxt[0]
    return {"in_m": round(o_in, 2), "out_m": round(o_out, 2), "s0": round(float(ss[lo]), 2), "s1": round(float(ss[hi]), 2),
            "stations_measured": len(rows), "stations_tried": int(round((s1 - s0) / STEP_M)) + 1,
            "block_amp_median": round(amp_med, 1),
            "width_p25_p75": [round(float(np.percentile([r[2] - r[1] for r in rows], q)), 2) for q in (25, 75)]}


def pct(v, q):
    v = sorted(v)
    return v[min(len(v) - 1, int(math.ceil(q / 100 * len(v))) - 1)]


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    tdir = Path(argv.pop(0))
    opt = {}
    while argv:
        k = argv.pop(0)
        opt[k] = argv.pop(0)
    E = Edge(tdir, opt["--image"], [float(v) for v in opt["--corners"].split(",")])
    truth = json.loads(Path(opt["--truth"]).read_text(encoding="utf-8"))["kerbs"] if "--truth" in opt else None
    specs = []
    if "--spans" in opt:
        for spec in opt["--spans"].split(","):
            f = spec.split(":")
            s0, s1 = (float(v) for v in f[1].split("-"))
            specs.append((f[0].upper()[0], s0, s1, f[2] if len(f) > 2 else None))
    else:
        for t in truth:
            e = t.get("s_eye") or [t["s0"], t["s1"]]
            specs.append((t["side"][0].upper(), float(e[0]), float(e[1]), t.get("colour")))
    kerbs, res = [], {"in": [], "out": [], "s0": [], "s1": [], "width": []}
    strip_rows = []
    for sd, s0, s1, colour in specs:
        side = 1 if sd == "L" else -1
        m = measure(E, side, s0, s1)
        tag = f"{sd} {s0:.0f}-{s1:.0f}"
        if m is None:
            print(f"[kerb_offsets] {tag}: no blocks measured")
            continue
        line = (f"[kerb_offsets] {tag}: s {m['s0']:.1f}-{m['s1']:.1f}  in {m['in_m']:+.2f} out {m['out_m']:+.2f} m  "
                f"({m['stations_measured']}/{m['stations_tried']} stations, block amp {m['block_amp_median']})")
        if truth is not None:
            t = next((t for t in truth if t["side"][0].upper() == sd and (t.get("s_eye") or [t["s0"]])[0] == s0), None)
            if t is not None:
                d = {"in": m["in_m"] - t["in_m"], "out": m["out_m"] - t["out_m"], "s0": m["s0"] - t["s0"],
                     "s1": m["s1"] - t["s1"], "width": (m["out_m"] - m["in_m"]) - (t["out_m"] - t["in_m"])}
                for key, v in d.items():
                    res[key].append(abs(v))
                    res.setdefault(f"{key}@{t.get('colour')}", []).append(abs(v))
                line += (f"  | truth in {t['in_m']:+.2f} out {t['out_m']:+.2f} s {t['s0']:.0f}-{t['s1']:.0f} {t.get('colour')}"
                         f"  d_in {d['in']:+.2f} d_out {d['out']:+.2f} d_s0 {d['s0']:+.1f} d_s1 {d['s1']:+.1f}")
                m["truth"] = {"in_m": t["in_m"], "out_m": t["out_m"], "s0": t["s0"], "s1": t["s1"], "colour": t.get("colour")}
        print(line)
        strip_rows.append((side, m, f"{sd} {s0:.0f}-{s1:.0f} {colour or ''}: read in {m['in_m']:+.2f} out {m['out_m']:+.2f} "
                           f"s {m['s0']:.1f}-{m['s1']:.1f} (yellow)" + (f" | truth in {m['truth']['in_m']:+.2f} out "
                           f"{m['truth']['out_m']:+.2f} s {m['truth']['s0']:.0f}-{m['truth']['s1']:.0f} (magenta)"
                           if "truth" in m else ""), m.get("truth")))
        ss = np.arange(m["s0"], m["s1"] + 1e-6, 2 * STEP_M)
        if ss[-1] < m["s1"]:
            ss = np.append(ss, m["s1"])
        lon, lat = E.lonlat(ss, side, np.array([0.0]))
        kerbs.append({"side": "left" if side == 1 else "right", "s0": m["s0"], "s1": m["s1"], "in_m": m["in_m"],
                      "out_m": m["out_m"], "colour": colour, "profile": PROFILE.get(colour, "kerb"), "s_eye": [s0, s1],
                      "stations_measured": m["stations_measured"],
                      "reader": {k: v for k, v in m.items() if k not in ("in_m", "out_m", "s0", "s1", "stations_measured")},
                      "edge_lonlat": [[round(float(a), 8), round(float(b), 8)] for a, b in zip(lon[:, 0], lat[:, 0])]})
    summary = None
    if truth is not None and res["in"]:
        summary = {k: {"n": len(v), "median": round(float(np.median(v)), 2), "p95": round(pct(v, 95), 2),
                       "max": round(max(v), 2)} for k, v in res.items()}
        for k, v in summary.items():
            print(f"[kerb_offsets] |residual| {k:17s}: n {v['n']}  median {v['median']:.2f}  p95 {v['p95']:.2f}  max {v['max']:.2f} m")
    if "--strips" in opt and strip_rows:
        strips(E, strip_rows, opt["--strips"])
        print(f"[kerb_offsets] strips -> {opt['--strips']}")
    if "--out" in opt:
        out = {"_doc": ("Racing kerbs measured off the aerial by their alternating blocks, colour not used (ledger 0081 round "
                        "3, tools/kerb_offsets.py), in tools/kerb_spans.py's shape: each run is the lane edge it lies along, "
                        "as lon/lat, plus where its paint sits across that edge (in_m / out_m: metres past the lane edge of "
                        "the live line's widths, - = inside). The build places it there with kerb.placement \"measured\"."),
               "imagery": opt.get("--imagery"), "image_m_per_px": round((E.ce - E.cw) * E.m_lon / E.W, 3),
               "method": opt.get("--how", "tools/kerb_offsets.py over spans checked by eye"),
               "line": "data/gate_centerline.json of the live track (engine frame)",
               "measurer": {"tool": "tools/kerb_offsets.py",
                            "params": {k: v for k, v in globals().items() if k.isupper() and k != "PROFILE"}},
               **({"calibration": summary} if summary else {}),
               "kerbs": kerbs}
        Path(opt["--out"]).write_text(json.dumps(out, indent=1), encoding="utf-8")
        print(f"[kerb_offsets] {len(kerbs)} runs, {sum(k['s1'] - k['s0'] for k in kerbs):.0f} m -> {opt['--out']}")


if __name__ == "__main__":
    main()

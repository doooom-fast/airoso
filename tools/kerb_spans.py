"""Kerb runs measured off a georeferenced aerial over hand-checked station spans (ledger 0080).

tools/aerial_edges.py FINDS kerb paint (and its windows fragment a run where a stripe fades); the spans it and the colour
scan find are checked by eye on tools/edge_sheet.py zooms and written down as "side:s0-s1:colour". This tool then MEASURES
each span off the same image, station by station on the track's own line (data/gate_centerline.json), and writes the
kerbs file the build reads (route.kerbs_file, tools/author_kerbs_blend.py):

  in_m / out_m   the median over the span's stations of the first / last kerb-paint offset across the lane edge, in the
                 band +-BAND_M (paint_class below, on the colour pair the span declares; blue / yellow: the blue
                 blocks only, since NAIP's stripe yellow is the dry grass's colour)
  edge_lonlat    the lane edge every 2 stations, lon/lat (a line change does not lose the run)
  colour         as checked by eye: blue_white, red_white, blue_yellow
  profile        "kerb" (raised: the config's kerb.height_m) or "paint" (flat paint on the asphalt edge; built flat,
                 since no height is seen); default by colour, PROFILE below

    python tools/kerb_spans.py <track-dir> --image <png> --corners W,N,E,S --spans "L:212-236:blue_white,..." \
           --imagery "<what, when, resolution>" --out <kerbs.json> [--how "<how the spans were checked>"]

Every number here is [invented] tuning of a colour reader (GATES-CHANGELOG 2026-11-05); the image is the measurement.
"""
from __future__ import annotations

import bisect
import json
import math
import sys
from pathlib import Path

from PIL import Image

STEP_M = 1.0
BAND_M = 2.5
OFF_STEP_M = 0.15
MIN_HITS = 2          # a station with fewer paint pixels in the band says nothing about the run's width
PROFILE = {"blue_white": "kerb", "red_white": "kerb", "blue_yellow": "paint"}


def mpd(lat0):
    phi = math.radians(lat0)
    return (111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi),
            111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi))


def paint_class(p):
    r, g, b = p[:3]
    mx, mn = max(r, g, b), min(r, g, b)
    if b > r + 25 and b > g:
        return "blue"
    if r > g + 25 and r > b + 20 and g < b + 25:
        return "red"
    if (r + g + b) / 3 >= 150 and mx - mn <= 50 and b >= r - 45:
        return "white"
    if r > b + 45 and g > b + 35 and mx >= 140:
        return "yellow"
    return None


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    tdir = Path(argv.pop(0))
    opt = {}
    while argv:
        k = argv.pop(0)
        opt[k] = argv.pop(0)
    img = Image.open(opt["--image"]).convert("RGB")
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
        s = max(0.0, min(st[-1], s))
        j = min(len(P) - 2, max(0, bisect.bisect_right(st, s) - 1))
        t = (s - st[j]) / ((st[j + 1] - st[j]) or 1.0)
        x = P[j][0] + (P[j + 1][0] - P[j][0]) * t
        n = P[j][2] + (P[j + 1][2] - P[j][2]) * t
        a, b = P[max(0, j - 1)], P[min(len(P) - 1, j + 2)]
        tx, tz = b[0] - a[0], b[2] - a[2]
        L = math.hypot(tx, tz) or 1.0
        return x, n, -tz / L, tx / L, (Wd[j] + (Wd[j + 1] - Wd[j]) * t) / 2.0

    def lonlat(s, side, o):
        x, n, lx, lz, hw = at(s)
        d = side * (hw + o)
        return lon0 + (x + lx * d) / m_lon, lat0 + (n + lz * d) / m_lat

    def sample(lon, lat):
        i, j = int(round((lon - cw) / (ce - cw) * W_)), int(round((cn - lat) / (cn - cs) * H_))
        return pix[i, j] if 0 <= i < W_ and 0 <= j < H_ else None

    offs = [-BAND_M + k * OFF_STEP_M for k in range(int(2 * BAND_M / OFF_STEP_M) + 1)]
    kerbs = []
    for spec in opt["--spans"].split(","):
        sd, rng, colour = spec.split(":")
        side = 1 if sd.upper().startswith("L") else -1
        s0, s1 = (float(v) for v in rng.split("-"))
        # blue / yellow: the yellow reads like the dry grass beside it, so the width is the blue blocks' alone
        want = {"blue", "white"} if colour == "blue_white" else {"red", "white"} if colour == "red_white" else {"blue"}
        ins, outs = [], []
        s = s0
        while s <= s1 + 1e-6:
            hits = []
            for o in offs:
                p = sample(*lonlat(s, side, o))
                if p is not None and paint_class(p) in want:
                    hits.append(o)
            if len(hits) >= MIN_HITS:
                ins.append(min(hits)); outs.append(max(hits))
            s += STEP_M
        if not ins:
            raise SystemExit(f"[kerb_spans] {spec}: no paint measured in the span")
        ins.sort(); outs.sort()
        k_in, k_out = ins[len(ins) // 2], outs[len(outs) // 2]
        ss = [s0 + i * 2 * STEP_M for i in range(int((s1 - s0) / (2 * STEP_M)) + 1)]
        if ss[-1] < s1:
            ss.append(s1)
        kerbs.append({"side": "left" if side == 1 else "right", "s0": s0, "s1": s1,
                      "in_m": round(k_in, 2), "out_m": round(k_out, 2), "colour": colour,
                      "profile": PROFILE[colour], "stations_measured": len(ins),
                      "edge_lonlat": [[round(v, 8) for v in lonlat(q, side, 0.0)] for q in ss]})
        print(f"[kerb_spans] {spec}: in {k_in:+.2f} out {k_out:+.2f} m over {len(ins)} stations")
    out = {"_doc": ("Racing kerbs and painted edge stripes measured off the aerial for the Lake Murray engine port (ledgers "
                    "0078, 0080). Each run is the lane edge it lies along, as lon/lat, plus where its paint sits across "
                    "that edge (in_m / out_m: metres past the lane edge of the live line's widths, - = inside). The build "
                    "places the run OUTSIDE the lane edge (tools/author_kerbs_blend.py); profile 'kerb' rises to the "
                    "config's kerb.height_m, 'paint' is laid flat."),
           "imagery": opt.get("--imagery"), "image_m_per_px": round((ce - cw) * m_lon / W_, 3),
           "method": opt.get("--how", "tools/kerb_spans.py over spans checked by eye"),
           "line": "data/gate_centerline.json of the live track (engine frame)",
           "measurer": {"tool": "tools/kerb_spans.py", "params": {k: v for k, v in globals().items() if k.isupper() and k != "PROFILE"}},
           "kerbs": kerbs}
    Path(opt["--out"]).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"[kerb_spans] {len(kerbs)} runs, {sum(k['s1'] - k['s0'] for k in kerbs):.0f} m -> {opt['--out']}")


if __name__ == "__main__":
    main()

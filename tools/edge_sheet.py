"""A contact sheet of aerial zooms along a circuit's line, to check traced kerbs / run-off by eye (ledger 0080; L12).

Each cell is a CELL_M square of the georeferenced aerial centred on one window's middle station, upsampled, with both
lane edges of the track's line (data/gate_centerline.json, its widths) in thin cyan, the window's stretch of the chosen
edge in magenta drawn MARK_OFF_M outside the lane (so the paint under it stays visible), and tick marks every 10 m. The
label is the window: side, s0-s1, and a free tag. Read it, then keep it beside the trace.

    python tools/edge_sheet.py <track-dir> --image <png> --corners W,N,E,S --windows "L:520-533:new,R:262-268" \
                               --out <sheet.jpg> [--cell-m 50] [--cols 4]
    --windows @<edges.traced.json>   every kerb run in a reader's output
"""
from __future__ import annotations

import bisect
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

CELL_M = 50.0
CELL_PX = 400
MARK_OFF_M = 3.0


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
    cell_m = float(opt.get("--cell-m", CELL_M))
    cols = int(opt.get("--cols", 4))
    img = Image.open(opt["--image"]).convert("RGB")
    W_, H_ = img.size
    cw, cn, ce, cs = (float(v) for v in opt["--corners"].split(","))
    local = json.loads((tdir / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    lon0, lat0 = float(local["origin"]["lon"]), float(local["origin"]["lat"])
    m_lon, m_lat = mpd(lat0)
    mpp = (ce - cw) * m_lon / W_

    def px(x, n):
        lon, lat = lon0 + x / m_lon, lat0 + n / m_lat
        return (lon - cw) / (ce - cw) * W_, (cn - lat) / (cn - cs) * H_

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

    def edge(s, side, off=0.0):
        x, n, lx, lz, hw = at(s)
        return x + lx * side * (hw + off), n + lz * side * (hw + off)

    spec = opt["--windows"]
    wins = []
    if spec.startswith("@"):
        for k in json.loads(Path(spec[1:]).read_text(encoding="utf-8"))["kerbs"]:
            wins.append((1 if k["side"] == "left" else -1, k["s0"], k["s1"], k.get("colour", "")))
    else:
        for w in spec.split(","):
            parts = w.split(":")
            a, b = parts[1].split("-")
            wins.append((1 if parts[0].upper().startswith("L") else -1, float(a), float(b),
                         parts[2] if len(parts) > 2 else ""))
    rows = math.ceil(len(wins) / cols)
    sheet = Image.new("RGB", (cols * CELL_PX, rows * (CELL_PX + 18)), (20, 20, 20))
    d0 = ImageDraw.Draw(sheet)
    half = cell_m / 2 / mpp
    for k, (side, s0, s1, tag) in enumerate(wins):
        cx, cy = px(*edge((s0 + s1) / 2, side)[:2])
        box = (int(cx - half), int(cy - half), int(cx + half), int(cy + half))
        crop = img.crop(box)
        sc = CELL_PX / crop.size[0]
        crop = crop.resize((CELL_PX, CELL_PX), Image.LANCZOS)
        d = ImageDraw.Draw(crop)

        def loc(x, n):
            X, Y = px(x, n)
            return (X - box[0]) * sc, (Y - box[1]) * sc
        lo, hi = (s0 + s1) / 2 - cell_m, (s0 + s1) / 2 + cell_m
        ss = [lo + i * 0.5 for i in range(int((hi - lo) / 0.5) + 1)]
        for sd in (1, -1):
            d.line([loc(*edge(s, sd)) for s in ss], fill=(0, 230, 230), width=1)
        d.line([loc(*edge(s0 + i * 0.5, side, MARK_OFF_M)) for i in range(int((s1 - s0) / 0.5) + 1)],
               fill=(255, 0, 255), width=3)
        for s in range(int(math.ceil(lo / 10) * 10), int(hi), 10):
            a, b = loc(*edge(s, side, MARK_OFF_M - 1.0)), loc(*edge(s, side, MARK_OFF_M + 1.5))
            d.line([a, b], fill=(255, 255, 0), width=1)
        r, c = divmod(k, cols)
        sheet.paste(crop, (c * CELL_PX, r * (CELL_PX + 18) + 18))
        d0.text((c * CELL_PX + 4, r * (CELL_PX + 18) + 3),
                f"{'L' if side == 1 else 'R'} s {s0:.0f}-{s1:.0f} {tag}", fill=(255, 255, 255))
    out = Path(opt["--out"])
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=85)
    print(f"[edge_sheet] {len(wins)} windows -> {out} ({cell_m:.0f} m cells, {mpp:.2f} m/px)")


if __name__ == "__main__":
    main()

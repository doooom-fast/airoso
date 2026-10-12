"""Pictures of the paint centreline on the aerial: before (the OSM line) and after (the paint centreline).

Lookout Lariat V3 (ledger 0048, P2), for Kevin: what moved and why, on the photograph itself. Per corner
(default C4, C9, C10): two panels of the same NAIP crop, left the OSM centreline in grey, right the paint
centreline in yellow, both over the painted white edge lines the aerial traced (white dots), with how far
each line sits from the traced painted centre line. Plus one overview of the whole climb (a NAIP window at
1.6 m per pixel fetched once into the window cache): OSM in grey, the paint centreline in yellow, the corner
names. Pictures only: nothing reads them.

Writes ``data/aerial/overlays/paint_<id>.png`` (256-colour palette PNGs; NAIP is public domain, credit
"USGS, USDA, The National Map: Orthoimagery"). No thresholds here.

    python tools/paint_pictures.py <project-dir> [--cache DIR] [--no-fetch] [--corner ID]... [--no-overview]
                                   [--centerline F] [--osm F] [--traces F] [--out-dir DIR]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "tools")):
    if p not in sys.path:
        sys.path.insert(0, p)
from PIL import Image, ImageDraw  # noqa: E402

import verify_centreline_paint as vp  # noqa: E402
from aerial import geo, naip, overlay  # noqa: E402
from aerial.context import Ctx  # noqa: E402

GREY = (150, 150, 150)
YELLOW = (255, 214, 0)
OVERVIEW = {"id": "climb_overview", "px_m": 1.6, "margin_m": 60.0, "st_m": [0.0, 7100.0]}


def _line_lonlat(path):
    gj = json.loads(Path(path).read_text(encoding="utf-8"))
    f = next((x for x in gj["features"] if (x.get("properties") or {}).get("kind") == "full"), gj["features"][0])
    return gj, [(float(c[0]), float(c[1])) for c in f["geometry"]["coordinates"]]


def _paint_xy(traces, w, key, levels=("high", "medium")):
    """A traced line's points (medium+) as lon/lat."""
    lon0, lat0 = traces["frame"]["origin_lonlat"]
    mlon, mlat = traces["frame"]["m_per_deg"]
    ln = w[key]
    return [(lon0 + x / mlon, lat0 + z / mlat) for (x, z), c in zip(ln["xz_m"], ln["confidence"]) if c in levels]


def _to_img(V, lon, lat):
    E, N = geo.to_utm(lon, lat)
    return E - V[0], N - V[1]


def _draw_poly(dr, P, pts, col, width, outline=None):
    seg = [P(*q) for q in pts]
    if outline:
        dr.line(seg, fill=outline, width=width + 2)
    dr.line(seg, fill=col, width=width)


def _scale_north(dr, im, px_per_m, fnt, metres=10):
    bar = metres * px_per_m
    y0 = im.size[1] - 18
    dr.rectangle([10, y0, 10 + bar, y0 + 5], fill=(255, 255, 255), outline=(0, 0, 0))
    dr.text((16 + bar, y0 - 6), f"{metres} m", fill=(255, 255, 255), font=fnt)
    xa = im.size[0] - 18
    dr.line([xa, y0 + 4, xa, y0 - 22], fill=(255, 255, 255), width=2)
    dr.polygon([(xa - 5, y0 - 16), (xa + 5, y0 - 16), (xa, y0 - 26)], fill=(255, 255, 255))
    dr.text((xa - 4, y0 - 42), "N", fill=(255, 255, 255), font=fnt)


def corner_picture(ctx, cid, osm_ll, new_ll, traces, S=2):
    W = ctx.win(cid)
    m = W.m
    V = traces["registration"]["osm_minus_imagery_EN_m"]
    win = next(w for w in traces["windows"] if w["id"] == cid)
    yc = (win.get("core") or {}).get("yellow_circle")
    am = json.loads((ctx.data / "aerial" / "aerial_measurements.json").read_text(encoding="utf-8"))
    rec = next(c for c in am["corners"] if c["id"] == cid)
    if rec.get("centre"):
        cx, cy = rec["centre"]["utm13n_nad83"]
    else:
        cx, cy = _to_img(V, *yc["centre_lonlat"])
    R = rec.get("radius_m") or (yc or {}).get("R_m") or 15.0
    half = R + 24.0
    x, y = naip.px_of(m, cx, cy)
    hp = half / m["px_m"]
    box = [int(max(0, x - hp)), int(max(0, y - hp)), int(min(W.W, x + hp)), int(min(W.H, y + hp))]
    crop = W.rgb_img.crop(box).resize(((box[2] - box[0]) * S, (box[3] - box[1]) * S), Image.BICUBIC)

    def P(lon, lat):
        E, N = _to_img(V, lon, lat)
        px, py = naip.px_of(m, E, N)
        return ((px - box[0] + 0.5) * S, (py - box[1] + 0.5) * S)

    def near(pts):
        xmin, ymin, xmax, ymax = m["bbox_utm13n"]
        out = []
        for q in pts:
            E, N = _to_img(V, *q)
            if xmin - 30 < E < xmax + 30 and ymin - 30 < N < ymax + 30:
                out.append(q)
        return out
    edges = _paint_xy(traces, win, "edge_left") + _paint_xy(traces, win, "edge_right")
    osm_line = vp.Line(osm_ll)
    new_line = vp.Line(new_ll)
    pts = vp.paint_points(traces, win)
    d_osm = [osm_line.distance(*p) for p in pts]
    d_new = [new_line.distance(*p) for p in pts]
    fnt = overlay.font(13)
    fnt_b = overlay.font(15)
    panels = []
    for title, ll, col, ds in (("Before: the OSM line", osm_ll, GREY, d_osm), ("After: the paint centreline", new_ll, YELLOW, d_new)):
        im = crop.copy()
        dr = ImageDraw.Draw(im, "RGBA")
        for q in edges:
            a = P(*q)
            dr.ellipse([a[0] - 1.6, a[1] - 1.6, a[0] + 1.6, a[1] + 1.6], fill=(255, 255, 255, 230))
        _draw_poly(dr, P, near(ll), col, 3, outline=(0, 0, 0))
        dr.rectangle([0, 0, im.size[0], 46], fill=(0, 0, 0, 180))
        dr.text((8, 5), f"{cid} {ctx.names.get(cid, '')}: {title}", fill=(255, 255, 255), font=fnt_b)
        dr.text((8, 25), "off the painted centre line: median %.2f m, worst %.2f m" % (sorted(ds)[len(ds) // 2], max(ds)),
                fill=col, font=fnt)
        _scale_north(dr, im, S / m["px_m"], fnt)
        panels.append(im)
    gap = 6
    out = Image.new("RGB", (panels[0].size[0] * 2 + gap, panels[0].size[1] + 30), (20, 20, 20))
    out.paste(panels[0], (0, 0))
    out.paste(panels[1], (panels[0].size[0] + gap, 0))
    dr = ImageDraw.Draw(out)
    dr.text((8, out.size[1] - 24), "white dots: the painted white edge lines as traced on NAIP 2019 (public domain, USGS, USDA, "
            "The National Map: Orthoimagery)", fill=(230, 230, 230), font=fnt)
    return out, {"window": cid, "osm_max_m": round(max(d_osm), 2), "new_max_m": round(max(d_new), 2),
                 "osm_median_m": round(sorted(d_osm)[len(d_osm) // 2], 2), "new_median_m": round(sorted(d_new)[len(d_new) // 2], 2)}


def overview_picture(ctx, osm_ll, new_ll, traces, new_props):
    V = traces["registration"]["osm_minus_imagery_EN_m"]
    L = ctx.L
    s0, s1 = OVERVIEW["st_m"]
    pts = [(p[0] - V[0], p[1] - V[1]) for p, s in zip(L.utm, L.st) if s0 <= s <= s1]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    mg = OVERVIEW["margin_m"]
    E0, N0 = round((min(xs) + max(xs)) / 2), round((min(ys) + max(ys)) / 2)
    hw, hh = round((max(xs) - min(xs)) / 2 + mg), round((max(ys) - min(ys)) / 2 + mg)
    m = naip.window(ctx.cache, OVERVIEW["id"], E0, N0, hw, hh, px=OVERVIEW["px_m"], fetch=ctx.fetch)
    W = naip.Win(m)
    S = 1
    im = W.rgb_img.copy()
    dr = ImageDraw.Draw(im, "RGBA")

    def P(lon, lat):
        E, N = _to_img(V, lon, lat)
        px, py = naip.px_of(m, E, N)
        return ((px + 0.5) * S, (py + 0.5) * S)
    src = new_props.get("osm_station_m") or []
    climb_new = [q for q, s in zip(new_ll, src) if s0 - 30 <= s <= s1 + 30] if src else new_ll
    climb_osm = [q for q, s in zip(osm_ll, L.st) if s0 - 30 <= s <= s1 + 30]
    for w in traces["windows"]:
        if not w.get("lap_st_m") or w["lap_st_m"][0] > s1:
            continue
        for q in _paint_xy(traces, w, "edge_left") + _paint_xy(traces, w, "edge_right"):
            a = P(*q)
            dr.point(a, fill=(255, 255, 255, 255))
    _draw_poly(dr, P, climb_osm, GREY, 4)
    _draw_poly(dr, P, climb_new, YELLOW, 2)
    fnt = overlay.font(14)
    fnt_b = overlay.font(18)
    for c in ctx.spec["corner_plan"]["corners"]:
        if not (s0 <= c["apex_st_m"] <= s1):
            continue
        E, N = L.utm[c["apex_v"]]
        a = P(*geo.from_utm(E, N))
        dr.text((a[0] + 9, a[1] - 9), c["id"], fill=(255, 255, 255), font=fnt_b, stroke_width=2, stroke_fill=(0, 0, 0))
    dr.rectangle([0, 0, im.size[0], 52], fill=(0, 0, 0, 185))
    dr.text((10, 6), "The Lariat climb (st 0-7,100): grey = the OSM line, yellow = the paint centreline", fill=(255, 255, 255), font=fnt_b)
    dr.text((10, 30), "white = painted edge lines traced on NAIP 2019 (USGS, USDA, The National Map: Orthoimagery)", fill=(230, 230, 230), font=fnt)
    _scale_north(dr, im, 1.0 / OVERVIEW["px_m"], fnt, metres=200)
    return im


def run(project_dir, cache=None, fetch=True, corners=None, overview=True, centerline=None, osm=None, traces_path=None,
        out_dir=None, log=print):
    ctx = Ctx(project_dir, cache, fetch)
    data = ctx.data
    _, osm_ll = _line_lonlat(osm or data / "centerline.osm.geojson")
    new_gj, new_ll = _line_lonlat(centerline or data / "centerline.geojson")
    new_props = next((x for x in new_gj["features"] if (x.get("properties") or {}).get("kind") == "full"),
                     new_gj["features"][0]).get("properties") or {}
    traces = json.loads(Path(traces_path or data / "aerial" / "paint_traces.json").read_text(encoding="utf-8"))
    ctx.V = tuple(traces["registration"]["osm_minus_imagery_EN_m"])
    out_dir = Path(out_dir) if out_dir else data / "aerial" / "overlays"
    stats = []
    for cid in corners or ["C4", "C9", "C10"]:
        im, st = corner_picture(ctx, cid, osm_ll, new_ll, traces)
        overlay.save_palette(im, out_dir / f"paint_{cid}.png")
        stats.append(st)
        log(f"[pictures] paint_{cid}.png: OSM worst {st['osm_max_m']} m, paint centreline worst {st['new_max_m']} m")
    if overview:
        im = overview_picture(ctx, osm_ll, new_ll, traces, new_props)
        overlay.save_palette(im, out_dir / "paint_climb.png")
        log("[pictures] paint_climb.png")
    return stats


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("project_dir")
    ap.add_argument("--cache")
    ap.add_argument("--no-fetch", action="store_true")
    ap.add_argument("--corner", action="append")
    ap.add_argument("--no-overview", action="store_true")
    ap.add_argument("--centerline")
    ap.add_argument("--osm")
    ap.add_argument("--traces")
    ap.add_argument("--out-dir")
    a = ap.parse_args(argv)
    try:
        run(a.project_dir, a.cache, not a.no_fetch, a.corner, not a.no_overview, a.centerline, a.osm, a.traces, a.out_dir)
    except (SystemExit, FileNotFoundError, KeyError) as e:
        print(f"[pictures] {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Overlay pictures for the aerial measurements: the imagery crop with the OSM lap line, every traced point
and the fitted result, so a reader can check each number against the photograph.

Colours: red = the OSM lap line and raw way nodes (moved into the imagery frame by the registration
offset); cyan / blue = inner / outer pavement edge points (grey = rejected); white = painted edge lines;
yellow = the double-yellow centre line; magenta = the result; the white wedge = the measured core.
Saved as 256-colour palette PNGs (small enough for the repo; NAIP is public domain).

No thresholds here (drawing only).
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import naip

COL = {"in": (0, 235, 255), "out": (60, 110, 255), "fog_in": (255, 255, 255), "fog_out": (255, 255, 255),
       "yel": (255, 225, 0), "osm": (255, 40, 40), "final": (255, 0, 255), "trace": (255, 150, 0)}


def font(sz):
    for f in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(f, sz)
        except Exception:
            pass
    return ImageFont.load_default()


def _legend_scale_north(dr, im, m, S, lines, fnt, line_h=15, pad=4, box_pad=None):
    hgt = line_h * len(lines) + (2 * pad if box_pad is None else box_pad)
    dr.rectangle([0, 0, im.size[0], hgt], fill=(0, 0, 0, 170))
    for i, t in enumerate(lines):
        dr.text((pad, pad + line_h * i), t, fill=(255, 255, 255, 255), font=fnt)
    bar = 10 / m["px_m"] * S
    y0 = im.size[1] - 16
    dr.rectangle([8, y0, 8 + bar, y0 + 5], fill=(255, 255, 255, 255), outline=(0, 0, 0, 255))
    dr.text((14 + bar, y0 - 6), "10 m", fill=(255, 255, 255, 255), font=fnt)
    xa = im.size[0] - 16
    dr.line([xa, y0 + 4, xa, y0 - 22], fill=(255, 255, 255, 255), width=2)
    dr.polygon([(xa - 5, y0 - 16), (xa + 5, y0 - 16), (xa, y0 - 26)], fill=(255, 255, 255, 255))
    dr.text((xa - 4, y0 - 42), "N", fill=(255, 255, 255, 255), font=fnt)


def draw_core(ctx, cid, core, final=None, S=2, label=None):
    res, fits, feats, rays = core["res"], core["fits"], core["feats"], core["rays"]
    W = ctx.win(cid)
    m = W.m
    c = core["c"]
    SHIFT = ctx.V
    Rv = max([f["R"] for f in fits.values() if f and f["R"] < 40] + [core["R"]])
    half_m = min(55.0, max(28.0, Rv + 16.0))
    x, y = naip.px_of(m, c[0], c[1])
    hp = half_m / m["px_m"]
    box = [int(max(0, x - hp)), int(max(0, y - hp)), int(min(W.W, x + hp)), int(min(W.H, y + hp))]
    S = max(S, -(-560 // max(1, box[2] - box[0])))
    im = W.rgb_img.crop(box).resize(((box[2] - box[0]) * S, (box[3] - box[1]) * S), Image.BICUBIC)
    dr = ImageDraw.Draw(im, "RGBA")

    def P(E, N):
        px, py = naip.px_of(m, E, N)
        return ((px - box[0] + 0.5) * S, (py - box[1] + 0.5) * S)

    def circ(cx, cy, R, col, w=1):
        q = P(cx, cy)
        r = R / m["px_m"] * S
        dr.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r], outline=col, width=w)

    a, b = res["span_lap"]
    lap_pts = [(p[0] - SHIFT[0], p[1] - SHIFT[1]) for p in ctx.L.utm_between(a - 120, b + 120)]
    dr.line([P(*p) for p in lap_pts], fill=COL["osm"] + (230,), width=2)
    xmin, ymin, xmax, ymax = m["bbox_utm13n"]
    for w in ctx.ways:
        for p in w["utm"]:
            p = (p[0] - SHIFT[0], p[1] - SHIFT[1])
            if xmin <= p[0] <= xmax and ymin <= p[1] <= ymax:
                q = P(*p)
                dr.rectangle([q[0] - 2, q[1] - 2, q[0] + 2, q[1] + 2], outline=COL["osm"] + (255,))
    for ray in (rays[0], rays[-1]):
        phi = ray["phi"]
        p0 = (c[0] + math.cos(phi) * 2.0, c[1] + math.sin(phi) * 2.0)
        p1 = (c[0] + math.cos(phi) * (Rv + 8), c[1] + math.sin(phi) * (Rv + 8))
        dr.line([P(*p0), P(*p1)], fill=(255, 255, 255, 120), width=1)
    for ray in rays:
        rr = ray["r"]
        for k, kk in (("e_lo", "in"), ("e_hi", "out")):
            if rr.get(k) is None:
                continue
            pt = (ray["p"][0] + ray["n"][0] * rr[k], ray["p"][1] + ray["n"][1] * rr[k])
            q = P(*pt)
            col = COL[kk] + (255,) if rr.get("q_" + k[2:]) == "ok" else (160, 160, 160, 200)
            dr.ellipse([q[0] - 1.6, q[1] - 1.6, q[0] + 1.6, q[1] + 1.6], fill=col)
    for k in ("fog_in", "fog_out", "yel"):
        for pt in feats[k]:
            q = P(*pt)
            dr.ellipse([q[0] - 1.1, q[1] - 1.1, q[0] + 1.1, q[1] + 1.1], fill=COL[k] + (230,))
    for k in ("in", "out"):
        f = fits.get(k)
        if f and f["R"] < 60:
            circ(f["cx"], f["cy"], f["R"], COL[k] + (200,), 1)
    for k in ("fog_in", "fog_out"):
        f = fits.get(k)
        if f and f["R"] < 60:
            circ(f["cx"], f["cy"], f["R"], (255, 255, 255, 150), 1)
    if fits.get("yel") and fits["yel"]["R"] < 60:
        circ(fits["yel"]["cx"], fits["yel"]["cy"], fits["yel"]["R"], COL["yel"] + (220,), 1)
    if final:
        circ(final["cx"], final["cy"], final["R"], COL["final"] + (255,), 3)
        q = P(final["cx"], final["cy"])
        dr.line([q[0] - 6, q[1], q[0] + 6, q[1]], fill=COL["final"], width=2)
        dr.line([q[0], q[1] - 6, q[0], q[1] + 6], fill=COL["final"], width=2)
    _legend_scale_north(dr, im, m, S, label or [cid], font(12))
    return im


def draw_junction(ctx, cid, jd, label=None, S=2, half_m=42.0):
    out, arms, best, X = jd["out"], jd["arms"], jd["best"], jd["X"]
    W = ctx.win(cid)
    m = W.m
    S0 = ctx.V
    x, y = naip.px_of(m, X[0], X[1])
    hp = half_m / m["px_m"]
    box = [int(max(0, x - hp)), int(max(0, y - hp)), int(min(W.W, x + hp)), int(min(W.H, y + hp))]
    im = W.rgb_img.crop(box).resize(((box[2] - box[0]) * S, (box[3] - box[1]) * S), Image.BICUBIC)
    dr = ImageDraw.Draw(im, "RGBA")

    def P(e, n):
        q = naip.px_of(m, e, n)
        return ((q[0] - box[0] + 0.5) * S, (q[1] - box[1] + 0.5) * S)
    apex = ctx.plan[cid]["apex_st_m"]
    dr.line([P(p[0] - S0[0], p[1] - S0[1]) for p in ctx.L.utm_between(apex - 80, apex + 80)], fill=(255, 40, 40, 230), width=2)
    xmin, ymin, xmax, ymax = m["bbox_utm13n"]
    for w in ctx.ways:
        for p in w["utm"]:
            p = (p[0] - S0[0], p[1] - S0[1])
            if xmin <= p[0] <= xmax and ymin <= p[1] <= ymax:
                q = P(*p)
                dr.rectangle([q[0] - 2, q[1] - 2, q[0] + 2, q[1] + 2], outline=(255, 40, 40, 255))
    for k, a in arms.items():
        for p in a["pts_in"]:
            q = P(*p)
            dr.ellipse([q[0] - 1.5, q[1] - 1.5, q[0] + 1.5, q[1] + 1.5], fill=(0, 235, 255, 255))
        for p in a["pts_out"]:
            q = P(*p)
            dr.ellipse([q[0] - 1.5, q[1] - 1.5, q[0] + 1.5, q[1] + 1.5], fill=(60, 110, 255, 255))
        ln = a["edge_in_line"]
        if ln:
            p0 = (ln["c"][0] - ln["d"][0] * 45, ln["c"][1] - ln["d"][1] * 45)
            p1 = (ln["c"][0] + ln["d"][0] * 45, ln["c"][1] + ln["d"][1] * 45)
            dr.line([P(*p0), P(*p1)], fill=(0, 235, 255, 110), width=1)
        lc = a["centre_line"]
        if lc:
            p0 = (lc["c"][0] - lc["d"][0] * 45, lc["c"][1] - lc["d"][1] * 45)
            p1 = (lc["c"][0] + lc["d"][0] * 45, lc["c"][1] + lc["d"][1] * 45)
            dr.line([P(*p0), P(*p1)], fill=(255, 225, 0, 110), width=1)
    if best:
        med, R, cc, pts, core = best
        for p in pts:
            q = P(p[0], p[1])
            dr.ellipse([q[0] - 1.2, q[1] - 1.2, q[0] + 1.2, q[1] + 1.2], fill=(200, 200, 200, 200))
        for p in core:
            q = P(p[0], p[1])
            dr.ellipse([q[0] - 1.8, q[1] - 1.8, q[0] + 1.8, q[1] + 1.8], fill=(0, 255, 255, 255))

        def circ(R_, col, w):
            q = P(*cc)
            r = R_ / m["px_m"] * S
            dr.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r], outline=col, width=w)
        circ(R, (0, 255, 255, 230), 1)
        if out.get("R_centreline"):
            circ(out["R_centreline"], (255, 0, 255, 255), 3)
        q = P(*cc)
        dr.line([q[0] - 6, q[1], q[0] + 6, q[1]], fill=(255, 0, 255), width=2)
        dr.line([q[0], q[1] - 6, q[0], q[1] + 6], fill=(255, 0, 255), width=2)
    _legend_scale_north(dr, im, m, S, label or [cid], font(12), box_pad=8)
    return im


def draw_crossing(ctx, ways, xs, xres, data, S=1.4, label=None):
    from . import crossings
    W = data["W"]
    m = W.m
    rows = data["rows"]
    st = xs["lap_st_m"]
    box = [0, 0, W.W, W.H]
    im = W.rgb_img.crop(box).resize((int((box[2] - box[0]) * S), int((box[3] - box[1]) * S)), Image.BICUBIC)
    dr = ImageDraw.Draw(im, "RGBA")

    def P(e, n):
        q = naip.px_of(m, e, n)
        return ((q[0] - box[0] + 0.5) * S, (q[1] - box[1] + 0.5) * S)
    for w in xs["draw_ways"]:
        dr.line([P(*p) for p in crossings.way_img(ctx, ways, w)], fill=(0, 255, 255, 170), width=1)
    V = ctx.V
    lp = [(p[0] - V[0], p[1] - V[1]) for p in ctx.L.utm_between(st - 120, st + 120)]
    dr.line([P(*p) for p in lp], fill=(255, 40, 40, 220), width=2)
    for r in rows:
        for side in ("lo", "hi"):
            if r.get("e_" + side) is not None:
                q = P(r["p"][0] + r["n"][0] * r["e_" + side], r["p"][1] + r["n"][1] * r["e_" + side])
                dr.ellipse([q[0] - 2, q[1] - 2, q[0] + 2, q[1] + 2], fill=(255, 0, 255, 255))
        for g in r["gaps"]:
            q = P(r["p"][0] + r["n"][0] * g[0], r["p"][1] + r["n"][1] * g[0])
            dr.ellipse([q[0] - 1.5, q[1] - 1.5, q[0] + 1.5, q[1] + 1.5], fill=(255, 255, 0, 255))
    for side in ("side_a", "side_b"):
        a, b = xres["deck_edges_near_lap"][side]["utm13n_nad83"]
        dr.line([P(*a), P(*b)], fill=(255, 0, 255, 255), width=3)
    _legend_scale_north(dr, im, m, S, label or [xs["id"]], font(13), line_h=16, box_pad=8)
    return im


def save_palette(im, path):
    """The repo copy: 256-colour palette PNG, no metadata."""
    im = im.convert("RGB")
    im.info = {}
    q = im.quantize(colors=256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
    q.info = {}
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    q.save(path, optimize=True)

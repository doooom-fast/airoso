"""Bridges over the lap (Lariat: C-470 over West Colfax and over US-6): deck width, edges, crossing angle and
the lap stretch under the deck.

The deck axis is the OSM bridge way moved into the imagery frame (minus the registration offset). Profiles
every 1 m across it, +-45 m along it; the deck is the bright low-NDVI concrete run through the axis, its
edges at the 50 % brightness crossing between the deck and the ground beside it; sections within +-15 m of
the lap kept, merged ones dropped; straight lines fitted to each edge; the lap line (imagery frame)
intersected with them. NAIP is rectified to bare earth, so an elevated deck's absolute footprint can sit
~2-4 m off (relief displacement); its width and angle hold.

Thresholds, all **[invented]** for the aerial pass (2026-10-11), none a gate:
- deck run: brightness >= 0.75 x the deck level at the axis (median +-10 samples) and NDVI < 0.05, dark gaps
  up to 1.2 m bridged (joints, gaps between parallel decks) [invented];
- internal dark line: a local minimum below 0.8 x the deck level, >= 1 m from the last [invented];
- sections within +-15 m of the lap; merged sections > 1.5 m over the median width dropped [invented];
- paved opening: along the sunlit deck edge 2 m outside it, NDVI < 0 and brightness >= 45, gaps <= 1.5 m
  [invented];
- the lap's paved corridor near the deck: NDVI < -0.05 and brightness >= 50 on 0.3 m samples, gaps <= 1.2 m
  [invented].
"""
from __future__ import annotations

import json
import math
import statistics as stt
from pathlib import Path

from . import circles, geo, profile as pf


def load_bridge_ways(path, ids):
    """{str(id): {tags, geometry}} for the named ways, in the payload's own order."""
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    out = {}
    for e in d["payload"]["elements"]:
        if e["type"] == "way" and e["id"] in ids:
            out[str(e["id"])] = {"tags": e.get("tags"), "geometry": e.get("geometry")}
    return out, {"fetched_utc": d.get("fetched_utc"), "query_fingerprint": d.get("query_fingerprint")}


def osm_crossings(ctx, ways):
    """Where each bridge way crosses the lap (OSM frame on the UTM grid, no datum shift)."""
    L = ctx.L

    def seg_x(a, b, c, d):
        r = (b[0] - a[0], b[1] - a[1])
        s = (d[0] - c[0], d[1] - c[1])
        den = r[0] * s[1] - r[1] * s[0]
        if abs(den) < 1e-12:
            return None
        t = ((c[0] - a[0]) * s[1] - (c[1] - a[1]) * s[0]) / den
        u = ((c[0] - a[0]) * r[1] - (c[1] - a[1]) * r[0]) / den
        if 0 <= t <= 1 and 0 <= u <= 1:
            return t, u
        return None
    res = []
    for wid, w in ways.items():
        pts = [geo.to_utm(n["lon"], n["lat"]) for n in w["geometry"]]
        blen = sum(geo.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
        for i in range(len(L.utm) - 1):
            a, b = L.utm[i], L.utm[i + 1]
            for j in range(len(pts) - 1):
                x = seg_x(a, b, pts[j], pts[j + 1])
                if x:
                    t, u = x
                    P = (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
                    st = L.st[i] + t * (L.st[i + 1] - L.st[i])
                    h1 = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
                    h2 = math.degrees(math.atan2(pts[j + 1][1] - pts[j][1], pts[j + 1][0] - pts[j][0]))
                    ang = abs(((h2 - h1 + 90) % 180) - 90)
                    along = sum(geo.dist(pts[k], pts[k + 1]) for k in range(j)) + u * geo.dist(pts[j], pts[j + 1])
                    res.append({"way": int(wid), "lap_st": round(st, 1), "utm": [round(P[0], 2), round(P[1], 2)],
                                "lonlat": [round(v, 7) for v in geo.from_utm(*P)],
                                "angle_deg": round(ang, 1), "lap_heading_deg_from_N": round((90 - h1) % 360, 1),
                                "bridge_heading_deg_from_N": round((90 - h2) % 360, 1),
                                "bridge_way_len_m": round(blen, 1), "crossing_at_m_along_way": round(along, 1),
                                "tags": {k: w["tags"].get(k) for k in ("name", "highway", "lanes", "layer", "oneway", "destination:ref")}})
    return res


def way_img(ctx, ways, wid):
    V = ctx.V
    return [(p[0] - V[0], p[1] - V[1]) for p in (geo.to_utm(n["lon"], n["lat"]) for n in ways[str(wid)]["geometry"])]


def analyze_deck(pr):
    o, br, nd = pr["o"], pr["br"], pr["nd"]
    n = len(o)
    i0 = min(range(n), key=lambda i: abs(o[i]))
    deck_level = stt.median([br[i] for i in range(max(0, i0 - 10), min(n, i0 + 11)) if br[i] is not None])
    thr_in = 0.75 * deck_level

    def grow(sgn):
        i = i0
        last = i0
        gap = 0
        while 0 <= i + sgn < n:
            i += sgn
            if br[i] is None:
                break
            if br[i] >= thr_in and (nd[i] is None or nd[i] < 0.05):
                last = i
                gap = 0
            else:
                gap += 1
                if gap * 0.15 > 1.2:
                    break
        return last
    a, b = grow(-1), grow(+1)
    res = {"deck_level": round(deck_level, 1)}
    for side, idx, sgn in (("lo", a, -1), ("hi", b, 1)):
        outs = [br[k] for k in range(idx + sgn * 4, idx + sgn * 14, sgn) if 0 <= k < n and br[k] is not None]
        lout = stt.median(outs) if outs else None
        if lout is None:
            res["e_" + side] = None
            continue
        level = 0.5 * (deck_level + lout)
        e = None
        for k in range(idx - sgn * 4, idx + sgn * 8, sgn):
            if not (0 <= k < n and 0 <= k + sgn < n) or br[k] is None or br[k + sgn] is None:
                continue
            if (br[k] - level) * (br[k + sgn] - level) <= 0 and br[k] != br[k + sgn]:
                t = (level - br[k]) / (br[k + sgn] - br[k])
                e = o[k] + t * (o[k + sgn] - o[k])
                break
        res["e_" + side] = e if e is not None else o[idx]
        res["out_" + side] = round(lout, 1)
    gaps = []
    for k in range(a + 3, b - 3):
        if br[k] is None:
            continue
        if br[k] < 0.8 * deck_level and br[k] <= min(br[k - 2:k + 3]):
            if not gaps or o[k] - gaps[-1][0] > 1.0:
                gaps.append((o[k], round(br[k] / deck_level, 2)))
    res["gaps"] = gaps
    return res


def deck_rows(ctx, ways, xid, axis_ways, lap_st, along=(-45, 45)):
    W = ctx.win(xid)
    V = ctx.V
    axis = pf.Poly(way_img(ctx, ways, axis_ways[0]))
    lp, lt = ctx.L.at(lap_st)
    lp = (lp[0] - V[0], lp[1] - V[1])
    best = min(((geo.dist(axis.pos(k * 0.5), lp), k * 0.5) for k in range(int(axis.L / 0.5) + 1)))
    s0 = best[1]
    rows = []
    for k in range(int(along[0]), int(along[1]) + 1):
        s = s0 + k
        if s < 0 or s > axis.L:
            continue
        p = axis.pos(s)
        t = axis.tan(s, 3.0)
        n = pf.left_normal(t)
        pr = pf.sample_profile(W, p, n, 30.0, 0.15)
        r = analyze_deck(pr)
        r.update({"k": k, "p": p, "n": n, "t": t})
        rows.append(r)
    return W, axis, s0, rows


def _lap_img_poly(ctx, st, half=150):
    V = ctx.V
    return pf.Poly([(p[0] - V[0], p[1] - V[1]) for p in ctx.L.utm_between(st - half, st + half)]), st - half


def _intersect_line_poly(ln, poly):
    (cx, cy), (dx, dy) = ln["c"], ln["d"]
    best = None
    for i in range(len(poly.p) - 1):
        a, b = poly.p[i], poly.p[i + 1]
        r = (b[0] - a[0], b[1] - a[1])
        den = r[0] * dy - r[1] * dx
        if abs(den) < 1e-12:
            continue
        t = ((cx - a[0]) * dy - (cy - a[1]) * dx) / den
        if 0 <= t <= 1:
            P = (a[0] + t * r[0], a[1] + t * r[1])
            s = poly.s[i] + t * (poly.s[i + 1] - poly.s[i])
            d = math.hypot(P[0] - cx, P[1] - cy)
            if best is None or d < best[0]:
                best = (d, P, s)
    return best


def _opening_along_edge(W, ln, P0, sgn_out, maxlen=60.0, off=2.0):
    (cx, cy), (dx, dy) = ln["c"], ln["d"]
    nx, ny = -dy * sgn_out, dx * sgn_out

    def cls(t):
        p = (P0[0] + dx * t + nx * off, P0[1] + dy * t + ny * off)
        s = W.sample(*p)
        if s is None:
            return None
        r, g, b, nir = s
        bb = (r + g + b) / 3
        nd = (nir - r) / (nir + r + 1e-6)
        if bb < 45:
            return "dark"
        return "paved" if nd < 0.0 else "veg"
    ends = []
    for sg in (-1, 1):
        t = 0.0
        last = 0.0
        gap = 0.0
        while abs(t) < maxlen:
            t += sg * 0.3
            c = cls(t)
            if c is None:
                break
            if c == "paved":
                last = t
                gap = 0.0
            else:
                gap += 0.3
                if gap > 1.5:
                    break
        ends.append(last)
    return ends


def measure(ctx, ways, xs):
    """One crossing (``xs`` = its spec entry). Returns (result, drawing data)."""
    xid, axis_ways, st = xs["id"], xs["axis_ways"], xs["lap_st_m"]
    V = ctx.V
    W, axis, s0, rows = deck_rows(ctx, ways, xid, axis_ways, st)
    near = [r for r in rows if abs(r["k"]) <= 15 and r.get("e_lo") is not None and r.get("e_hi") is not None]
    w = [r["e_hi"] - r["e_lo"] for r in near]
    wmed = stt.median(w)
    near = [r for r in near if abs((r["e_hi"] - r["e_lo"]) - wmed) <= 1.5]
    w = sorted(r["e_hi"] - r["e_lo"] for r in near)
    lo = [(r["p"][0] + r["n"][0] * r["e_lo"], r["p"][1] + r["n"][1] * r["e_lo"]) for r in near]
    hi = [(r["p"][0] + r["n"][0] * r["e_hi"], r["p"][1] + r["n"][1] * r["e_hi"]) for r in near]
    Llo, Lhi = circles.robust_line(lo), circles.robust_line(hi)
    lap_poly, s_base = _lap_img_poly(ctx, st)
    xlo = _intersect_line_poly(Llo, lap_poly)
    xhi = _intersect_line_poly(Lhi, lap_poly)
    st_lo = s_base + xlo[2]
    st_hi = s_base + xhi[2]
    smid = 0.5 * (xlo[2] + xhi[2])
    lt = lap_poly.tan(smid, 5.0)
    at = axis.tan(s0, 5.0)
    ang = math.degrees(math.acos(min(1.0, abs(lt[0] * at[0] + lt[1] * at[1]))))
    gaps = [g[0] for r in near for g in r["gaps"]]
    sunlit = xs["sunlit_side"]
    side_ln = Lhi if sunlit == "hi" else Llo
    P0 = (xhi if sunlit == "hi" else xlo)[1]
    other_ln = Llo if sunlit == "hi" else Lhi
    nx, ny = -side_ln["d"][1], side_ln["d"][0]
    v = (side_ln["c"][0] - other_ln["c"][0], side_ln["c"][1] - other_ln["c"][1])
    sgn_out = 1 if nx * v[0] + ny * v[1] > 0 else -1
    ends = _opening_along_edge(W, side_ln, P0, sgn_out)
    opening = ends[1] - ends[0]

    def ll(p):
        q = geo.from_utm(p[0] + V[0], p[1] + V[1])
        return [round(q[0], 7), round(q[1], 7)]

    def edge_seg(ln, P):
        (dx, dy) = ln["d"]
        a = (P[0] - dx * 25, P[1] - dy * 25)
        b = (P[0] + dx * 25, P[1] + dy * 25)
        return {"utm13n_nad83": [[round(a[0], 2), round(a[1], 2)], [round(b[0], 2), round(b[1], 2)]], "lonlat_wgs84": [ll(a), ll(b)],
                "fit_rms_m": round(ln["rms"], 2), "n": ln["n"]}
    head = (90 - math.degrees(math.atan2(at[1], at[0]))) % 360
    res = {
        "name": xs["name"], "window": xid, "osm_ways_over_lap": axis_ways, "osm_ways_all_on_structure": xs["ways_on_structure"],
        "lap_stations_under_deck_m": [round(min(st_lo, st_hi), 1), round(max(st_lo, st_hi), 1)],
        "lap_length_under_deck_m": round(abs(st_hi - st_lo), 1),
        "deck_width_m": {"median": round(stt.median(w), 2), "p10": round(w[int(0.1 * (len(w) - 1))], 2),
                         "p90": round(w[int(0.9 * (len(w) - 1))], 2), "n_sections": len(w),
                         "how": "bright-concrete run across the deck axis, 50 % brightness crossing each side, sections within +-15 m of the lap"},
        "deck_axis_heading_deg_from_N": round(head, 1) if head < 180 else round(head - 180, 1),
        "crossing_angle_deg": round(ang, 1),
        "deck_edges_near_lap": {"side_a": edge_seg(Llo, xlo[1]), "side_b": edge_seg(Lhi, xhi[1])},
        "longitudinal_dark_lines_m_from_axis": sorted(set(round(g, 1) for g in gaps)),
        "paved_opening_along_sunlit_edge_m": round(opening, 1),
        "paved_opening_note": "length, along the deck edge 2 m outside the deck on its sunlit side, of the continuous paved/sidewalk surface (NDVI < 0) the lap's corridor makes under the structure; the span must clear at least this; abutment faces themselves are not visible from above",
    }
    return res, {"W": W, "axis": axis, "s0": s0, "rows": rows}


def corridor(ctx, wid, st, half=35.0):
    """The lap's paved corridor across its own axis at lap station st (right -, left +)."""
    W = ctx.win(wid)
    V = ctx.V
    p, t = ctx.L.at(st)
    p = (p[0] - V[0], p[1] - V[1])
    n = pf.left_normal(t)
    pr = pf.sample_profile(W, p, n, half, 0.3)
    o = pr["o"]
    paved = [(nd is not None and br is not None and br >= 50 and nd < -0.05) for nd, br in zip(pr["nd"], pr["br"])]
    i0 = min(range(len(o)), key=lambda i: abs(o[i]))

    def grow(sg):
        i = i0
        last = i0
        gap = 0
        while 0 <= i + sg < len(o):
            i += sg
            if paved[i]:
                last = i
                gap = 0
            else:
                gap += 1
                if gap * 0.3 > 1.2:
                    break
        return o[last]
    a, b = grow(-1), grow(1)
    return [round(a, 1), round(b, 1), round(b - a, 1)]

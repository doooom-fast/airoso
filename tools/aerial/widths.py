"""Road width at stations along the lap (Lariat: the climb, Golden, Paradise Rd).

Per station: a 50 x 50 m window (``spec.windows``, ``W<st>``), profiles every 0.5 m across +-18 m of road
(the OSM line +-22 m, moving average +-4 m, moved onto the traced yellow when >= 25 % of profiles found it),
the asphalt model from the lane interiors (or, with no yellow, from the road middle +-1.5 m where brightness
> 60 and NDVI < -0.1), then per profile the yellow line, both white edge lines and both pavement edges.
Two widths: edge line to edge line (the painted travelled way) and pavement (to where the surface stops
matching the window's asphalt: an upper bound, gravel and dirt can read as asphalt at 0.6 m).

Thresholds, all **[invented]** for the aerial pass (2026-10-11), none a gate:
- +-18 m of road per station (``HALF_LEN_M``) [invented];
- reference moved onto the yellow only with >= 25 % yellow profiles [invented];
- despike: a value more than 0.5 m from the median of its +-4 neighbours is dropped [invented];
- a statistic needs >= 5 values [invented]; a station is "usable" with >= 10 profiles of either width
  (``report``) [invented].
"""
from __future__ import annotations

import math
import statistics as stt

from . import geo, profile as pf

HALF_LEN_M = 18.0


def win_id(st):
    return "W%05d" % int(st)


def measure_station(ctx, st, half_len=HALF_LEN_M):
    L = ctx.L
    wid = win_id(st)
    W = ctx.win(wid)
    ref = pf.Poly(L.utm_between(st - half_len - 4, st + half_len + 4)).smooth(4.0)
    recs = pf.trace2(W, ref, 2, ref.L - 2, None, search=4.0)
    ref2, nk = pf.refine_from_yellow(ref, recs)
    if nk >= 0.25 * len(recs):
        ref = ref2
    recs = pf.trace2(W, ref, 0, ref.L, None, search=2.0)
    model = pf.build_model(recs)
    if model is None:
        smp = []
        for r in recs:
            pr = r["pr"]
            for i, o in enumerate(pr["o"]):
                if abs(o) <= 1.5 and pr["nd"][i] is not None and pr["br"][i] > 60 and pr["nd"][i] < -0.1:
                    smp.append((pr["nd"][i], pr["ch"][i], pr["br"][i]))
        model = pf.Model(smp) if len(smp) > 50 else None
    rows = []
    for r in recs:
        pr = r["pr"]
        rr = r["r"] or {}
        y = rr.get("yellow")
        centre = y if y is not None else 0.0
        row = {"s": r["s"], "yellow": y, "yellow_prom": rr.get("yellow_prom")}
        for side, sgn in (("lo", -1), ("hi", 1)):
            f, fp = pf.find_fog(pr, centre, sgn) if y is not None else (None, None)
            row["fog_" + side] = f
            if model is not None:
                start = (f + sgn * 0.45) if f is not None else centre + sgn * 1.5
                e, q, outside = pf.find_edge(pr, model, start, sgn)
            else:
                e, q, outside = None, "no_model", None
            row["e_" + side] = e
            row["q_" + side] = q
            row["out_" + side] = outside
        rows.append(row)
    for key in ("e_lo", "e_hi", "fog_lo", "fog_hi"):
        _despike(rows, key)
    W_ = [r["e_hi"] - r["e_lo"] for r in rows if r["e_lo"] is not None and r["e_hi"] is not None and r["q_lo"] == "ok" and r["q_hi"] == "ok"]
    F_ = [r["fog_hi"] - r["fog_lo"] for r in rows if r["fog_lo"] is not None and r["fog_hi"] is not None]
    LL = [r["yellow"] - r["fog_lo"] for r in rows if r["fog_lo"] is not None and r["yellow"] is not None]
    LR = [r["fog_hi"] - r["yellow"] for r in rows if r["fog_hi"] is not None and r["yellow"] is not None]
    SL = [r["fog_lo"] - r["e_lo"] for r in rows if r["fog_lo"] is not None and r["e_lo"] is not None and r["q_lo"] == "ok"]
    SR = [r["e_hi"] - r["fog_hi"] for r in rows if r["fog_hi"] is not None and r["e_hi"] is not None and r["q_hi"] == "ok"]
    n = len(rows)
    sh = sum(1 for r in rows if r["q_lo"] == "shadow" or r["q_hi"] == "shadow")
    dark = {side: sum(1 for r in rows if (r.get("out_" + side) or {}).get("dark_then_bright")) for side in ("lo", "hi")}
    outv = {side: _med([(r.get("out_" + side) or {}).get("ndvi") for r in rows if r["q_" + side] == "ok"]) for side in ("lo", "hi")}
    p, t = L.at(st)
    res = {"station_m": st, "window": wid, "utm": [round(p[0], 2), round(p[1], 2)],
           "lonlat": [round(x, 7) for x in geo.from_utm(*p)],
           "heading_deg_from_east": round(math.degrees(math.atan2(t[1], t[0])), 1),
           "profiles": n, "pavement_width": _stats(W_), "edge_line_width": _stats(F_),
           "lane_right_of_travel": _stats(LL), "lane_left_of_travel": _stats(LR),
           "beyond_edge_line_right": _stats(SL), "beyond_edge_line_left": _stats(SR),
           "yellow_found_frac": round(sum(1 for r in rows if r["yellow"] is not None) / max(1, n), 2),
           "shadow_frac": round(sh / max(1, n), 2),
           "dark_band_beyond_edge_frac": {"right": round(dark["lo"] / max(1, n), 2), "left": round(dark["hi"] / max(1, n), 2)},
           "outside_ndvi_median": {"right": _r(outv["lo"]), "left": _r(outv["hi"])},
           "model": model.as_dict() if model else None}
    return {"res": res, "rows": rows, "ref": ref.p}


def _r(v):
    return None if v is None else round(v, 3)


def _med(v):
    v = [x for x in v if x is not None]
    return stt.median(v) if v else None


def _despike(rows, key, half=4, tol=0.5):
    vals = [r.get(key) for r in rows]
    for i, v in enumerate(vals):
        if v is None:
            continue
        nb = [vals[j] for j in range(max(0, i - half), min(len(vals), i + half + 1)) if j != i and vals[j] is not None]
        if len(nb) >= 3 and abs(v - stt.median(nb)) > tol:
            rows[i][key] = None
            if key.startswith("e_"):
                rows[i]["q_" + key[2:]] = "spike"


def _stats(v):
    if len(v) < 5:
        return None
    v = sorted(v)

    def q(f):
        return v[min(len(v) - 1, int(f * (len(v) - 1) + 0.5))]
    return {"median": round(stt.median(v), 2), "p10": round(q(0.1), 2), "p90": round(q(0.9), 2), "n": len(v)}

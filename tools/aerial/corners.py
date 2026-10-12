"""Hairpin cores (C1-C10 on the Lariat): radius, centre, edge pair, apex cross-section, paint traces.

Per corner (``spec.corner_plan``: the traced stretch [a, b] and the OSM core vertices come from the P0
fitter run, so the measurement never depends on its own result):

1. **Perpendicular trace** (``trace_corner``): profiles every 0.5 m normal to a reference that starts as the
   OSM lap line (moving average +-4 m, twice) and is moved onto the traced double-yellow line in three
   passes (search +-4.0, 2.5, 1.5 m). A polar pass through the apex (rays from the OSM core circle's centre,
   iterated on the yellow paint) replaces the reference along the arc where the yellow sits on the fitted
   circle. Then the window's asphalt model is built and the final trace finds the edge lines and edges.
2. **Turn and core** (``measure``): entry / exit headings from the traced legs (the circular mean over 8 m
   at each end of the stretch +-15 m) give the turn, unwrapped toward the OSM turn; the core is headings
   20-80 % of the turn (tools/fit_hairpins.py's own core), mapped to polar angles about the centre.
3. **Centre**: rays every 1 deg over the core from each seed (the perpendicular trace's yellow circle, a
   manual seed, the polar whole-arc circle, the OSM core circle) find the yellow peak; robust circle,
   iterated to a 0.02 m shift; the best trial scores coverage - 2 x rms.
4. **Rays every 0.5 deg** over the core: yellow, both white edge lines, both pavement edges on each ray.
5. **Fits**: one robust circle per feature; concentric pairs (``circles.concentric``) for the pavement
   edges and the painted edge lines. The decision rule and confidence live in ``record`` (below).

Shadowed apexes (``spec.force_ridge``): a yellow-paint ridge map (Y minus its 2.7 m box blur, on sunlit
asphalt only) and a grid search for the circle whose arc over the core is the strongest ridge
(``ridge_search``), seeded by ``spec.manual_seeds``.

Thresholds, all **[invented]** for the aerial pass (2026-10-11), none a gate:
- corner stretch: traced from 25 m before the stretch to 25 m after (``LEAD_M``) [invented];
- polar pass: OSM core circle used when R < 60 m; arc points within 4 m of it; yellow within 0.6 m of the
  fitted circle marks the arc (>= 8 points) [invented];
- legs: headings over 8 m (``LEG_M``) at each end of the stretch +-15 m (``PAD_M``) [invented];
- core: 20-80 % of the turn [invented in tools/fit_hairpins.py];
- centre iteration: yellow search +-3.0 m on the first ray pass then +-1.5 m, trimming max(0.35 m, 2.5 rms),
  stop at 0.02 m shift, 5 rounds [invented];
- feature fits trimmed at max(0.3 m, 2.5 rms); a fit is "good" with >= 45 % of the core rays used, rms
  <= 0.35 m and an arc >= 40 % of the core [invented];
- despike of ray features: +-6 neighbours, 0.5 m [invented];
- radius profile: circles through the traced yellow within +-5 m every 2 m, >= 12 points [invented];
- ridge map: box blur radius 4 px (2.7 m), sunlit = mean RGB > 55, asphalt = NDVI < -0.08 (blurred),
  grid +-4 m in 0.5 m steps, radii 0.75-1.35 x seed in 0.25 m steps, >= 30 % of the arc sunlit [invented];
- the radius decision and confidence: see ``record``.
"""
from __future__ import annotations

import math
import statistics as stt

from . import circles, geo, profile as pf

LEAD_M = 25.0
PAD_M = 15.0
LEG_M = 8.0


# ---------------------------------------------------------------- polar helpers (the arc pass)
def polar_profile(W, c, phi, r0, r1, ds=pf.DS):
    """Profile along the ray at angle phi from centre c, offsets o = r - rmid (inner side negative)."""
    rmid = 0.5 * (r0 + r1)
    p = (c[0] + math.cos(phi) * rmid, c[1] + math.sin(phi) * rmid)
    n = (math.cos(phi), math.sin(phi))
    return pf.sample_profile(W, p, n, 0.5 * (r1 - r0), ds), rmid


def yellow_arc(W, c, R, phis, search=4.5):
    pts = []
    for phi in phis:
        pr, rmid = polar_profile(W, c, phi, max(0.5, R - 10.0), R + 10.0)
        y, prom = pf.find_yellow(pr, prefer=R - rmid, search=search)
        if y is not None:
            r = rmid + y
            pts.append((c[0] + math.cos(phi) * r, c[1] + math.sin(phi) * r, phi, prom))
    return pts


def refine_centre(W, c, R, phis, iters=4):
    """Iterate: rays from c, yellow peaks, robust circle -> new (c, R)."""
    search = 4.5
    hist = []
    pts = []
    for it in range(iters):
        pts = yellow_arc(W, c, R, phis, search)
        f = circles.robust_circle([(p[0], p[1]) for p in pts], k=2.5, floor=0.4)
        if f is None:
            break
        hist.append({"it": it, "n": f["n"], "R": round(f["R"], 2), "rms": round(f["rms"], 3),
                     "shift": round(math.hypot(f["cx"] - c[0], f["cy"] - c[1]), 2)})
        c, R = (f["cx"], f["cy"]), f["R"]
        search = 2.0
    return c, R, hist, pts


def arc_reference(ref, c, R, pts, tol=0.6):
    """Replace the part of ref that runs along the arc with the arc itself (angles where the yellow sits on
    the fitted circle), then smooth. Returns (new Poly, arc info) or (ref, None)."""
    on = sorted(p[2] for p in pts if abs(math.hypot(p[0] - c[0], p[1] - c[1]) - R) <= tol)
    if len(on) < 8:
        return ref, None
    on = sorted(on)
    gaps = [(on[i + 1] - on[i], i) for i in range(len(on) - 1)] + [(on[0] + 2 * math.pi - on[-1], len(on) - 1)]
    g, gi = max(gaps)
    a0 = on[(gi + 1) % len(on)]
    a1 = on[gi]
    if a1 < a0:
        a1 += 2 * math.pi
    m = max(8, int((a1 - a0) * R / 0.5))
    arc = [(c[0] + R * math.cos(a0 + (a1 - a0) * k / m), c[1] + R * math.sin(a0 + (a1 - a0) * k / m)) for k in range(m + 1)]

    def proj_s(p):
        best = None
        for k in range(0, int(ref.L / 0.5) + 1):
            s = k * 0.5
            q = ref.pos(s)
            d = geo.dist(p, q)
            if best is None or d < best[0]:
                best = (d, s)
        return best[1]
    sa, sb = proj_s(arc[0]), proj_s(arc[-1])
    if sa > sb:
        arc.reverse()
        sa, sb = sb, sa
    pts_out = [ref.pos(k * 0.5) for k in range(0, int(sa / 0.5) - 6)] + arc + \
              [ref.pos(k * 0.5) for k in range(int(sb / 0.5) + 7, int(ref.L / 0.5) + 1)]
    return pf.Poly(pts_out).smooth(3.0), (math.degrees(a0), math.degrees(a1), sa, sb)


# ---------------------------------------------------------------- 1. perpendicular trace
def trace_corner(ctx, cid, lead=LEAD_M):
    L = ctx.L
    c = ctx.plan[cid]
    W = ctx.win(cid)
    a, b = c["span"]["st_m"]
    s_lo = a - lead
    ref = pf.Poly(L.utm_between(s_lo, b + lead)).smooth(4.0, iters=2)
    recs = pf.trace2(W, ref, 0, ref.L, None, search=4.0)
    for search in (2.5, 1.5):
        ref, nk = pf.refine_from_yellow(ref, recs)
        recs = pf.trace2(W, ref, 0, ref.L, None, search=search)
    meas = c.get("measured") or {}
    cv = meas.get("core_v") or [c["apex_v"] - 3, c["apex_v"] + 3]
    core_pts = [L.utm[v] for v in range(cv[0], cv[1] + 1)]
    f0 = geo.fit_circle(core_pts) if len(core_pts) >= 3 else None
    ctx.polar[cid] = None
    if f0 and f0[2] < 60:
        cx, cy, R0 = f0[0], f0[1], f0[2]
        sv = c["span"]["v"]
        angs = [math.atan2(L.utm[v][1] - cy, L.utm[v][0] - cx) for v in range(sv[0], sv[1] + 1)
                if abs(math.hypot(L.utm[v][0] - cx, L.utm[v][1] - cy) - R0) < 4.0]
        if len(angs) >= 3:
            angs = pf.unwrap(angs)
            a0, a1 = min(angs), max(angs)
            phis = [a0 - 0.35 + k * math.radians(1.0) for k in range(int((a1 - a0 + 0.7) / math.radians(1.0)) + 1)]
            cc, RR, hist, ypts = refine_centre(W, (cx, cy), R0, phis)
            ref2, arcinfo = arc_reference(ref, cc, RR, ypts)
            ctx.polar[cid] = {"osm_core_circle": [round(cx, 2), round(cy, 2), round(R0, 2)], "centre": cc,
                              "R_yellow": RR, "hist": hist, "arc": arcinfo, "n_yellow": len(ypts)}
            if arcinfo:
                ref = ref2
                recs = pf.trace2(W, ref, 0, ref.L, None, search=2.0)
                ref, nk = pf.refine_from_yellow(ref, recs)
                recs = pf.trace2(W, ref, 0, ref.L, None, search=1.5)
    model = pf.build_model(recs)
    recs = pf.trace2(W, ref, 0, ref.L, model, search=1.5)
    for key in ("e_lo", "e_hi", "fog_lo", "fog_hi", "yellow"):
        pf.despike(recs, key)
    ctx.models[cid] = model
    return W, ref, recs, s_lo, (a, b)


# ---------------------------------------------------------------- 2-5. the core
def ang_norm(a):
    while a > math.pi:
        a -= 2 * math.pi
    while a < -math.pi:
        a += 2 * math.pi
    return a


def leg_headings(ref, s_a, s_b, L=LEG_M):
    hin = [ref.heading(s_a + k * 0.5, 1.0) for k in range(int(L / 0.5))]
    hout = [ref.heading(s_b - k * 0.5, 1.0) for k in range(int(L / 0.5))]

    def circ_mean(v):
        return math.atan2(sum(math.sin(x) for x in v), sum(math.cos(x) for x in v))
    return circ_mean(hin), circ_mean(hout)


def polar_ray(W, c, phi, R, half=10.0):
    r0 = max(0.6, R - half)
    r1 = R + half
    rmid = 0.5 * (r0 + r1)
    p = (c[0] + math.cos(phi) * rmid, c[1] + math.sin(phi) * rmid)
    n = (math.cos(phi), math.sin(phi))
    pr = pf.sample_profile(W, p, n, 0.5 * (r1 - r0))
    return pr, rmid, p, n


def analyze_ray(pr, model, prior, search=2.0):
    """prior: expected yellow offset on this profile. Returns a dict of offsets (profile frame)."""
    res = {}
    y, prom = pf.find_yellow(pr, prefer=prior, search=search)
    if y is None:
        res["yellow_proxy"] = True
        yy = prior
    else:
        res["yellow"] = y
        res["yellow_prom"] = round(prom, 1)
        yy = y
    for side, sgn in (("lo", -1), ("hi", 1)):
        f, fp = pf.find_fog(pr, yy, sgn)
        if f is not None:
            res["fog_" + side] = f
            res["fog_prom_" + side] = round(fp, 1)
        start = (f + sgn * 0.45) if f is not None else (yy + sgn * 2.2)
        e, q, outside = pf.find_edge(pr, model, start, sgn)
        res["e_" + side] = e
        res["q_" + side] = q
        res["out_" + side] = outside
    return res


def _stats(v):
    if not v:
        return None
    v = sorted(v)

    def q(f):
        return v[min(len(v) - 1, int(f * (len(v) - 1) + 0.5))]
    return {"median": round(stt.median(v), 2), "p10": round(q(0.1), 2), "p90": round(q(0.9), 2), "n": len(v)}


def turn_rule(ctx, cid):
    """How a corner's turn is taken (``spec.turn_rule``): "legs" = from the traced entry and exit legs,
    unwrapped toward the OSM turn (robust where the reference through the apex is disturbed: shadow, a
    parked car); "reference" = the heading of the paint-anchored reference integrated over the stretch."""
    rules = ctx.spec.get("turn_rule") or {}
    return rules.get(cid, rules.get("_default", "legs"))


def measure(ctx, cid, trace, ridge=None):
    """The core measurement on a ``trace_corner`` result. ``ridge`` = a ``ridge_search`` result forced
    first (shadowed apex). Raises RuntimeError when no centre seed converges (a corner in deep shadow)."""
    W, ref, recs, s_lo, span = trace
    rule = turn_rule(ctx, cid)
    model = ctx.models.get(cid)
    a, b = span
    s_a = max(0.0, a - s_lo - PAD_M)
    s_b = min(ref.L, b - s_lo + PAD_M)
    h_in, h_out = leg_headings(ref, s_a, s_b)
    ss = [s_a + k * 0.5 for k in range(int((s_b - s_a) / 0.5) + 1)]
    th = pf.unwrap([ref.heading(s, 2.0) for s in ss])
    Th_ref = th[-1] - th[0]
    osm_turn = math.radians((ctx.plan[cid].get("measured") or {}).get("turn_deg") or math.degrees(Th_ref))
    d0 = ang_norm(h_out - h_in)
    if rule == "reference":
        Th = Th_ref
        th0 = th[0]
    else:
        Th = min((d0 + k * 2 * math.pi for k in (-1, 0, 1)), key=lambda v: abs(v - osm_turn))
        th = [th[0] - (th[0] - h_in)] + th[1:]
        th0 = h_in
    sgn = 1 if Th > 0 else -1           # +1 = left (CCW)

    def phi_of(h):  # polar angle of a point travelling with heading h on a circle
        return h - sgn * math.pi / 2
    phi_a = phi_of(th0 + 0.2 * Th)
    core_s = [s for s, t in zip(ss, th) if 0.2 <= (t - th[0]) / Th_ref <= 0.8]
    ypts = [pf.pt_at(r, r["r"]["yellow"]) for r in recs if r["r"] and r["r"].get("yellow") is not None
            and core_s and core_s[0] <= r["s"] <= core_s[-1]]
    f0 = circles.robust_circle(ypts) if len(ypts) >= 8 else None
    seeds = []
    if f0 and f0["R"] < 60:
        seeds.append(("perp-trace yellow", (f0["cx"], f0["cy"]), f0["R"]))
    ms = (ctx.spec.get("manual_seeds") or {}).get(cid)
    if ms:
        seeds.append(("manual (read off the zoomed imagery)", (ms[0], ms[1]), ms[2]))
    pol = ctx.polar.get(cid) or {}
    if pol.get("centre") and pol.get("R_yellow", 99) < 60:
        seeds.append(("polar whole-arc yellow", tuple(pol["centre"]), pol["R_yellow"]))
    if pol.get("osm_core_circle"):
        oc = pol["osm_core_circle"]
        seeds.append(("OSM core circle", (oc[0], oc[1]), oc[2]))
    dphi = math.radians(0.5) * sgn
    nphi = int(abs(0.6 * Th) / math.radians(0.5)) + 1
    phis = [phi_a + k * dphi for k in range(nphi)]

    def iterate(c, R):
        hist = []
        for it in range(5):
            pts = []
            for phi in phis[::2]:
                pr, rmid, p, n = polar_ray(W, c, phi, R)
                y, prom = pf.find_yellow(pr, prefer=R - rmid, search=3.0 if it == 0 else 1.5)
                if y is not None:
                    pts.append((p[0] + n[0] * y, p[1] + n[1] * y))
            f = circles.robust_circle(pts, k=2.5, floor=0.35)
            if f is None:
                break
            hist.append({"it": it, "n": f["n"], "n_rays": len(phis[::2]), "R": round(f["R"], 3), "rms": round(f["rms"], 3),
                         "shift": round(math.hypot(f["cx"] - c[0], f["cy"] - c[1]), 3)})
            c, R = (f["cx"], f["cy"]), f["R"]
            if hist[-1]["shift"] < 0.02:
                break
        return c, R, hist
    trials = []
    for name, c0_, R0_ in seeds:
        c1_, R1_, h_ = iterate(c0_, R0_)
        if h_:
            score = h_[-1]["n"] / h_[-1]["n_rays"] - 2.0 * h_[-1]["rms"]
            trials.append((score, name, c1_, R1_, h_, (round(c0_[0], 2), round(c0_[1], 2), round(R0_, 2))))
    trials.sort(key=lambda t: -t[0])
    if ridge is not None:
        trials.insert(0, (99.0, "yellow-ridge circle search (shadowed apex)", tuple(ridge["centre"]), ridge["R"],
                          [{"it": 0, "n": 0, "n_rays": 0, "R": ridge["R"], "rms": None, "shift": 0.0}],
                          tuple(ridge["centre"]) + (ridge["R"],)))
    if not trials:
        raise RuntimeError(f"{cid}: no seed converged")
    _, sname, c, R, hist, s0 = trials[0]
    seed = {"chosen": sname, "seed": s0, "trials": [{"seed": t[1], "score": round(t[0], 3), "R": round(t[3], 2),
                                                     "final": t[4][-1]} for t in trials]}
    rays = []
    for phi in phis:
        pr, rmid, p, n = polar_ray(W, c, phi, R)
        rr = analyze_ray(pr, model, R - rmid)
        rays.append({"phi": phi, "p": p, "n": n, "rmid": rmid, "r": rr})
    for key in ("e_lo", "e_hi", "fog_lo", "fog_hi", "yellow"):
        pf.despike(rays, key, half=6, tol=0.5)
    feats = {"in": [], "out": [], "fog_in": [], "fog_out": [], "yel": []}
    widths, fogw, lane_in, lane_out = [], [], [], []
    for ray in rays:
        rr = ray["r"]

        def P(off, ray=ray):
            return (ray["p"][0] + ray["n"][0] * off, ray["p"][1] + ray["n"][1] * off)
        if rr.get("q_lo") == "ok" and rr.get("e_lo") is not None:
            feats["in"].append(P(rr["e_lo"]))
        if rr.get("q_hi") == "ok" and rr.get("e_hi") is not None:
            feats["out"].append(P(rr["e_hi"]))
        if rr.get("fog_lo") is not None:
            feats["fog_in"].append(P(rr["fog_lo"]))
        if rr.get("fog_hi") is not None:
            feats["fog_out"].append(P(rr["fog_hi"]))
        if rr.get("yellow") is not None:
            feats["yel"].append(P(rr["yellow"]))
        if rr.get("q_lo") == "ok" and rr.get("q_hi") == "ok" and rr.get("e_lo") is not None and rr.get("e_hi") is not None:
            widths.append(rr["e_hi"] - rr["e_lo"])
        if rr.get("fog_lo") is not None and rr.get("fog_hi") is not None:
            fogw.append(rr["fog_hi"] - rr["fog_lo"])
            if rr.get("yellow") is not None:
                lane_in.append(rr["yellow"] - rr["fog_lo"])
                lane_out.append(rr["fog_hi"] - rr["yellow"])
    fits = {k: circles.robust_circle(v, k=2.5, floor=0.3) for k, v in feats.items()}
    nr = len(rays)
    cov = {k: round(len(v) / max(1, nr), 2) for k, v in feats.items()}
    used_cov = {k: (round(fits[k]["n"] / max(1, nr), 2) if fits[k] else 0.0) for k in feats}

    def good(k, minc=0.45, maxrms=0.35):
        f = fits[k]
        return bool(f and used_cov[k] >= minc and f["rms"] <= maxrms and f["span_deg"] >= 0.4 * abs(math.degrees(0.6 * Th)))

    def pair(k1, k2):
        f1, f2 = fits[k1], fits[k2]
        return {"R": 0.5 * (f1["R"] + f2["R"]), "centre_gap": math.hypot(f1["cx"] - f2["cx"], f1["cy"] - f2["cy"]),
                "R_in": f1["R"], "R_out": f2["R"]}
    est = {}
    if good("in") and good("out"):
        est["pavement_edges_mean"] = pair("in", "out")
    if good("fog_in") and good("fog_out"):
        est["edge_lines_mean"] = pair("fog_in", "fog_out")
    if good("yel"):
        est["yellow_line"] = {"R": fits["yel"]["R"]}
    res = {
        "id": cid, "turn_deg": round(math.degrees(Th), 1), "turn_ref_integrated_deg": round(math.degrees(Th_ref), 1),
        "turn_rule": rule,
        "direction": "left" if sgn > 0 else "right",
        "entry_heading_deg": round(math.degrees(h_in), 1), "exit_heading_deg": round(math.degrees(h_out), 1),
        "core_polar_deg": [round(math.degrees(phi_a), 1), round(math.degrees(phis[-1]), 1)],
        "core_arc_deg": round(abs(math.degrees(0.6 * Th)), 1), "n_rays": nr,
        "seed": seed, "centre_iterations": hist,
        "centre_utm": [round(c[0], 2), round(c[1], 2)], "coverage": cov, "used_coverage": used_cov,
        "fits": {k: (None if f is None else {"R": round(f["R"], 2), "rms": round(f["rms"], 3), "n": f["n"],
                                             "span_deg": round(f["span_deg"], 1),
                                             "centre_utm": [round(f["cx"], 2), round(f["cy"], 2)]}) for k, f in fits.items()},
        "good": {k: good(k) for k in feats},
        "estimates": {k: {kk: round(vv, 2) for kk, vv in v.items()} for k, v in est.items()},
        "width_core": _stats(widths), "edge_line_width_core": _stats(fogw),
        "lane_inner_core": _stats(lane_in), "lane_outer_core": _stats(lane_out),
        "model": model.as_dict() if model else None,
        "s_lo_lap": s_lo, "span_lap": span,
    }
    yel_all = [(r["s"], pf.pt_at(r, r["r"]["yellow"])) for r in recs if r["r"] and r["r"].get("yellow") is not None]
    prof = []
    s = s_a
    while s <= s_b + 1e-9:
        pts = [p for (q, p) in yel_all if abs(q - s) <= 5.0]
        f = geo.fit_circle(pts) if len(pts) >= 12 else None
        k_ = (1.0 / f[2]) if (f and f[2] < 1e4) else None
        if k_ is not None:
            dh = ang_norm(ref.heading(s + 2.0, 1.0) - ref.heading(s - 2.0, 1.0))
            k_ = k_ if dh * sgn >= 0 else -k_
        prof.append({"lap_st": round(s + s_lo, 1), "R_10m": (round(1 / k_, 2) if k_ else None), "n": len(pts)})
        s += 2.0
    res["radius_profile_yellow"] = prof
    return {"res": res, "rays": rays, "fits": fits, "feats": feats, "c": c, "R": R, "ref": ref.p,
            "recs": [{k: v for k, v in r.items() if k != "pr"} for r in recs], "s_lo": s_lo}


# ---------------------------------------------------------------- shadowed apex: ridge search
def ridge_map(W):
    from PIL import Image, ImageFilter
    rgb = W.rgb_img
    w, h = rgb.size
    px = rgb.load()
    cir = Image.open(W.cir_path).convert("RGB").load()
    Y = Image.new("L", (w, h))
    B = Image.new("F", (w, h))
    N = Image.new("L", (w, h))
    yp, bp, np_ = Y.load(), B.load(), N.load()
    for j in range(h):
        for i in range(w):
            r, g, b = px[i, j]
            nir = cir[i, j][0]
            yp[i, j] = int(max(0, min(255, (r + g) / 2.0 - b + 60)))
            bp[i, j] = (r + g + b) / 3.0
            np_[i, j] = int(max(0, min(255, ((nir - r) / (nir + r + 1e-6) + 1) * 127.5)))
    Yb = Y.filter(ImageFilter.BoxBlur(4))     # 9 px = 2.7 m box
    Nb = N.filter(ImageFilter.BoxBlur(3))
    yb, nb = Yb.load(), Nb.load()
    R = Image.new("F", (w, h))
    rp = R.load()
    for j in range(h):
        for i in range(w):
            v = yp[i, j] - yb[i, j]
            ok = bp[i, j] > 55 and (nb[i, j] / 127.5 - 1) < -0.08
            rp[i, j] = max(0.0, v) if ok else -1.0     # -1 = no evidence (shadow / not on asphalt)
    return R


def _ridge_score(Rm, m, c, Rad, phis):
    from . import naip
    rp = Rm.load()
    w, h = Rm.size
    tot = 0.0
    n = 0
    nall = 0
    for phi in phis:
        E = c[0] + Rad * math.cos(phi)
        N = c[1] + Rad * math.sin(phi)
        x, y = naip.px_of(m, E, N)
        xi, yi = int(round(x)), int(round(y))
        nall += 1
        if 0 <= xi < w and 0 <= yi < h:
            v = rp[xi, yi]
            if v >= 0:
                tot += v
                n += 1
    return (tot / n if n else 0.0), n / max(1, nall)


def ridge_search(W, c0, R0, phis, half=4.0, step=0.5, Rr=(0.75, 1.35), Rstep=0.25, min_frac=0.3):
    Rm = ridge_map(W)
    best = None
    k = int(half / step)
    Rs = [R0 * Rr[0] + i * Rstep for i in range(int((R0 * (Rr[1] - Rr[0])) / Rstep) + 1)]
    for a in range(-k, k + 1):
        for b in range(-k, k + 1):
            c = (c0[0] + a * step, c0[1] + b * step)
            for Rad in Rs:
                s, frac = _ridge_score(Rm, W.m, c, Rad, phis)
                if frac < min_frac:
                    continue
                if best is None or s > best[0]:
                    best = (s, c, Rad, frac)
    s, c, Rad, frac = best
    for st in (0.25, 0.1):
        improved = True
        while improved:
            improved = False
            for dc in ((st, 0, 0), (-st, 0, 0), (0, st, 0), (0, -st, 0), (0, 0, st), (0, 0, -st)):
                c2 = (c[0] + dc[0], c[1] + dc[1])
                R2 = Rad + dc[2]
                s2, f2 = _ridge_score(Rm, W.m, c2, R2, phis)
                if f2 >= min_frac and s2 > s:
                    s, c, Rad, frac = s2, c2, R2, f2
                    improved = True
    prof = [(round(Rad + d, 2), round(_ridge_score(Rm, W.m, c, Rad + d, phis)[0], 2)) for d in [x * 0.25 for x in range(-8, 9)]]
    return {"centre": c, "R": Rad, "score": s, "sunlit_frac": frac, "score_vs_R": prof}


def ridge_for(ctx, cid, core):
    """The ridge search over a measured core, seeded from ``spec.manual_seeds`` when the corner has one,
    else from the core's own centre and radius."""
    res = core["res"]
    a0, a1 = [math.radians(x) for x in res["core_polar_deg"]]
    n = int(abs(a1 - a0) / math.radians(1.0)) + 1
    phis = [a0 + (a1 - a0) * k / (n - 1) for k in range(n)]
    ms = (ctx.spec.get("manual_seeds") or {}).get(cid)
    if ms and cid in (ctx.spec.get("force_ridge") or []):
        c0, R0 = (ms[0], ms[1]), ms[2]
    else:
        c0, R0 = tuple(res["centre_utm"]), core["R"]
    return ridge_search(ctx.win(cid), c0, R0, phis)


# ---------------------------------------------------------------- edge appearance and leg widths
def edge_stats(core):
    rays = core["rays"]
    n = len(rays)
    rec = {}
    for side, nm in (("lo", "inner"), ("hi", "outer")):
        q = [r["r"].get("q_" + side) for r in rays]
        outs = [r["r"].get("out_" + side) or {} for r in rays if r["r"].get("q_" + side) == "ok"]
        nd = [o.get("ndvi") for o in outs if o.get("ndvi") is not None]
        ch = [o.get("chroma") for o in outs if o.get("chroma") is not None]
        dk = sum(1 for o in outs if o.get("dark_then_bright"))
        gap = [abs(r["r"]["e_" + side] - r["r"]["fog_" + side]) for r in rays
               if r["r"].get("q_" + side) == "ok" and r["r"].get("fog_" + side) is not None and r["r"].get("e_" + side) is not None]
        rec[nm] = {"edge_ok_frac": round(q.count("ok") / n, 2), "shadow_frac": round(q.count("shadow") / n, 2),
                   "open_frac": round(q.count("open") / n, 2),
                   "outside_ndvi_med": round(stt.median(nd), 2) if nd else None,
                   "outside_chroma_med": round(stt.median(ch), 2) if ch else None,
                   "narrow_dark_band_beyond_edge_frac": round(dk / n, 2),
                   "edge_line_to_pavement_edge_m_med": round(stt.median(gap), 2) if gap else None}
    return rec


def leg_widths(core):
    """Edge-line widths on the traced legs before and after the corner stretch (>= 8 profiles) [invented]."""
    res = core["res"]
    s_lo = core["s_lo"]
    a, b = res["span_lap"]
    legs = {"entry": [], "exit": []}
    for r in core["recs"]:
        rr = r["r"] or {}
        st = r["s"] + s_lo
        if rr.get("fog_lo") is None or rr.get("fog_hi") is None:
            continue
        w = rr["fog_hi"] - rr["fog_lo"]
        if st < a - 2:
            legs["entry"].append((st, w, rr.get("yellow")))
        elif st > b + 2:
            legs["exit"].append((st, w, rr.get("yellow")))
    rec = {}
    for k, v in legs.items():
        if len(v) >= 8:
            ws = sorted(x[1] for x in v)
            rec[k] = {"lap_st_range": [round(min(x[0] for x in v)), round(max(x[0] for x in v))],
                      "edge_line_width_median": round(stt.median(ws), 2),
                      "p10": round(ws[int(0.1 * (len(ws) - 1))], 2), "p90": round(ws[int(0.9 * (len(ws) - 1))], 2), "n": len(ws)}
    return rec

"""Junction corners (C12, C13 on the Lariat): the lap turns through an intersection, so the corner is a
kerb-return fillet, not a painted arc.

Model: the inside pavement edges of both arms are two straight lines; the fillet is a circular arc tangent
to both (its centre on their bisector: one parameter, R). R_fillet is fitted to the traced inside-corner
edge (rays from the fillet centre walking out of the grass to the first sustained asphalt); the lap
centreline radius is R_fillet + d, d = the arms' inside half-width (arm centre line to inside edge).

Thresholds, all **[invented]** for the aerial pass (2026-10-11), none a gate:
- arms traced 10-42 m either side of the apex (``ARM_NEAR_M`` / ``ARM_FAR_M``) [invented];
- an arm's reference moves onto its yellow line only when >= 30 % of its profiles found it [invented];
- asphalt model from the lap line +-1.8 m every 1 m where brightness > 60 and NDVI < -0.1 [invented];
- the inside-corner edge: the first of >= 4 consecutive asphalt samples (z <= 3, brightness > 45) on rays
  every 1 deg over the turn +-10 deg [invented];
- R scanned 3-33 m in 0.5 m steps, then +-0.6 m in 0.1 m about the best, scored by the median absolute
  residual of the core points (within 60 % of the half turn of the bisector), >= 10 core points [invented];
- uncertainty: half the R band within 0.15 m of the best median residual, + 0.3 m, + 0.5 m [invented].
"""
from __future__ import annotations

import math
import statistics as stt

from . import circles, profile as pf

ARM_NEAR_M = 10.0
ARM_FAR_M = 42.0


def arm_profiles(ctx, W, s0, s1, model):
    """Perpendicular profiles along the lap line between lap stations s0..s1 (a straight arm)."""
    L = ctx.L
    ref = pf.Poly(L.utm_between(min(s0, s1) - 3, max(s0, s1) + 3)).smooth(3.0)
    recs = pf.trace2(W, ref, 3, ref.L - 3, None, search=4.0)
    ref2, nk = pf.refine_from_yellow(ref, recs)
    if nk >= 0.3 * len(recs):
        ref = ref2
    recs = pf.trace2(W, ref, 0, ref.L, None, search=2.0)
    out = []
    for r in recs:
        pr = r["pr"]
        y = (r["r"] or {}).get("yellow")
        centre = y if y is not None else 0.0
        row = {"s": r["s"], "p": r["p"], "n": r["n"], "yellow": y, "yellow_prom": (r["r"] or {}).get("yellow_prom")}
        for side, sgn in (("lo", -1), ("hi", 1)):
            f, fp = pf.find_fog(pr, centre, sgn) if y is not None else (None, None)
            start = (f + sgn * 0.45) if f is not None else centre + sgn * 1.5
            e, q, outside = pf.find_edge(pr, model, start, sgn)
            row["e_" + side] = e
            row["q_" + side] = q
            row["fog_" + side] = f
        out.append(row)
    return ref, out


def model_from_lap(ctx, W, s0, s1):
    smp = []
    ref = pf.Poly(ctx.L.utm_between(s0, s1))
    s = 0.0
    while s < ref.L:
        p = ref.pos(s)
        n = pf.left_normal(ref.tan(s))
        pr = pf.sample_profile(W, p, n, 3.0)
        for i, o in enumerate(pr["o"]):
            if abs(o) <= 1.8 and pr["nd"][i] is not None and pr["br"][i] > 60 and pr["nd"][i] < -0.1:
                smp.append((pr["nd"][i], pr["ch"][i], pr["br"][i]))
        s += 1.0
    return pf.Model(smp)


def measure(ctx, cid, arm_near=ARM_NEAR_M, arm_far=ARM_FAR_M):
    c = ctx.plan[cid]
    W = ctx.win(cid)
    st = c["apex_st_m"]
    turn = math.radians(c["measured"]["turn_deg"])
    sgn = 1 if turn > 0 else -1          # +1 left
    inner = "hi" if sgn > 0 else "lo"     # left normal = 'hi'
    model = model_from_lap(ctx, W, st - arm_far, st + arm_far)
    arms = {}
    for name, (s0, s1) in (("in", (st - arm_far, st - arm_near)), ("out", (st + arm_near, st + arm_far))):
        ref, rows = arm_profiles(ctx, W, s0, s1, model)
        pts_in = [pf.pt_at(r, r["e_" + inner]) for r in rows if r["e_" + inner] is not None and r["q_" + inner] == "ok"]
        outer = "lo" if inner == "hi" else "hi"
        pts_out = [pf.pt_at(r, r["e_" + outer]) for r in rows if r["e_" + outer] is not None and r["q_" + outer] == "ok"]
        yel = [pf.pt_at(r, r["yellow"]) for r in rows if r["yellow"] is not None]
        mid = [pf.pt_at(r, 0.5 * (r["e_lo"] + r["e_hi"])) for r in rows
               if r["e_lo"] is not None and r["e_hi"] is not None and r["q_lo"] == "ok" and r["q_hi"] == "ok"]
        widths = [r["e_hi"] - r["e_lo"] for r in rows if r["e_lo"] is not None and r["e_hi"] is not None
                  and r["q_lo"] == "ok" and r["q_hi"] == "ok"]
        fogw = [r["fog_hi"] - r["fog_lo"] for r in rows if r["fog_lo"] is not None and r["fog_hi"] is not None]
        ln_in = circles.robust_line(pts_in) if len(pts_in) >= 8 else None
        ln_c = circles.robust_line(yel) if len(yel) >= 8 else (circles.robust_line(mid) if len(mid) >= 8 else None)
        d_half = None
        if ln_in and ln_c:
            p = ln_c["c"]
            q = ln_in["c"]
            d = ln_in["d"]
            d_half = abs((p[0] - q[0]) * -d[1] + (p[1] - q[1]) * d[0])
        arms[name] = {"rows": rows, "ref": ref.p, "s_range_lap": [s0, s1], "edge_in_line": ln_in, "centre_line": ln_c,
                      "centre_from": "yellow" if len(yel) >= 8 else "pavement middle",
                      "n_yellow": len(yel), "width_med": stt.median(widths) if widths else None, "n_width": len(widths),
                      "width_p10_p90": [sorted(widths)[int(0.1 * (len(widths) - 1))], sorted(widths)[int(0.9 * (len(widths) - 1))]] if widths else None,
                      "edge_lines_width_med": stt.median(fogw) if fogw else None,
                      "d_half_inside": d_half, "pts_in": pts_in, "pts_out": pts_out}
    A, B = arms["in"]["edge_in_line"], arms["out"]["edge_in_line"]

    def intersect(l1, l2):
        (x1, y1), (dx1, dy1) = l1["c"], l1["d"]
        (x2, y2), (dx2, dy2) = l2["c"], l2["d"]
        den = dx1 * dy2 - dy1 * dx2
        if abs(den) < 1e-9:
            return None
        t = ((x2 - x1) * dy2 - (y2 - y1) * dx2) / den
        return (x1 + t * dx1, y1 + t * dy1)
    X = intersect(A, B)

    def orient(l, toward):
        d = l["d"]
        v = (toward[0] - l["c"][0], toward[1] - l["c"][1])
        return d if d[0] * v[0] + d[1] * v[1] > 0 else (-d[0], -d[1])
    dA = orient(A, X)
    dB = orient(B, X)
    dB = (-dB[0], -dB[1])
    angle = math.degrees(math.atan2(dA[0] * dB[1] - dA[1] * dB[0], dA[0] * dB[0] + dA[1] * dB[1]))
    nA = (-dA[1] * sgn, dA[0] * sgn)
    nB = (-dB[1] * sgn, dB[0] * sgn)
    bis = (nA[0] + nB[0], nA[1] + nB[1])
    bl = math.hypot(*bis)
    bis = (bis[0] / bl, bis[1] / bl)
    half_turn = math.radians(abs(angle)) / 2.0

    def centre_for(R):
        k = R / math.cos(half_turn)
        return (X[0] + bis[0] * k, X[1] + bis[1] * k)

    def corner_edge(cc, R):
        pts = []
        phi_mid = math.atan2(-bis[1], -bis[0])
        span = math.radians(abs(angle)) / 2.0 + math.radians(10)
        k = 0
        while True:
            phi = phi_mid - span + k * math.radians(1.0)
            if phi > phi_mid + span:
                break
            k += 1
            n = (math.cos(phi), math.sin(phi))
            rr = 0.8
            run = 0
            found = None
            while rr < R + 15:
                p = (cc[0] + n[0] * rr, cc[1] + n[1] * rr)
                s = W.sample(*p)
                if s is None:
                    break
                r_, g_, b_, nir = s
                bb = (r_ + g_ + b_) / 3.0
                z = model.z((nir - r_) / (nir + r_ + 1e-6), ((r_ + g_) / 2 - b_) / max(bb, 1), bb)
                if z <= pf.Z_THR and bb > pf.SHADOW_BRI:
                    run += 1
                    if run == 1:
                        found = rr
                    if run >= 4:
                        break
                else:
                    run = 0
                    found = None
                rr += 0.15
            if found is not None and run >= 4:
                pts.append((cc[0] + n[0] * found, cc[1] + n[1] * found, phi))
        return pts
    best = None
    scan = []
    Rs = [3.0 + i * 0.5 for i in range(0, 61)]

    def evalR(R):
        cc = centre_for(R)
        pts = corner_edge(cc, R)
        pm = math.atan2(-bis[1], -bis[0])
        core = [p for p in pts if abs(math.atan2(math.sin(p[2] - pm), math.cos(p[2] - pm))) <= 0.6 * half_turn]
        if len(core) < 10:
            return None
        res = [math.hypot(p[0] - cc[0], p[1] - cc[1]) - R for p in core]
        med = stt.median([abs(v) for v in res])
        return (med, R, cc, pts, core)
    for R in Rs:
        e = evalR(R)
        if e is None:
            continue
        scan.append((round(R, 2), round(e[0], 3), len(e[4])))
        if best is None or e[0] < best[0]:
            best = e
    if best:
        R0 = best[1]
        for k in range(-6, 7):
            e = evalR(R0 + k * 0.1)
            if e is None:
                continue
            scan.append((round(R0 + k * 0.1, 2), round(e[0], 3), len(e[4])))
            if e[0] < best[0]:
                best = e
        scan.sort()
    out = {"id": cid, "turn_osm_deg": c["measured"]["turn_deg"], "inside_edge_lines_angle_deg": round(angle, 1),
           "X_inside_edges_utm": [round(X[0], 2), round(X[1], 2)], "model": model.as_dict(), "scan": scan}
    if best:
        med, R, cc, pts, core = best
        fc = circles.robust_circle([(p[0], p[1]) for p in core], k=2.5, floor=0.3, min_n=8)
        out.update({"R_fillet": round(R, 2), "fillet_centre_utm": [round(cc[0], 2), round(cc[1], 2)],
                    "fillet_median_abs_resid_m": round(med, 3), "n_core_pts": len(core),
                    "free_circle_check": None if not fc else {"R": round(fc["R"], 2), "rms": round(fc["rms"], 3), "n": fc["n"],
                                                               "centre_gap_m": round(math.hypot(fc["cx"] - cc[0], fc["cy"] - cc[1]), 2)}})
        dh = [arms[k]["d_half_inside"] for k in ("in", "out") if arms[k]["d_half_inside"] is not None]
        out["d_half_inside_m"] = {k: (round(arms[k]["d_half_inside"], 2) if arms[k]["d_half_inside"] is not None else None) for k in ("in", "out")}
        if dh:
            out["R_centreline"] = round(R + sum(dh) / len(dh), 2)
        out["arms"] = {k: {"width_med": round(v["width_med"], 2) if v["width_med"] else None, "n_width": v["n_width"],
                           "width_p10_p90": [round(x, 2) for x in v["width_p10_p90"]] if v["width_p10_p90"] else None,
                           "edge_lines_width_med": round(v["edge_lines_width_med"], 2) if v["edge_lines_width_med"] else None,
                           "centre_from": v["centre_from"], "n_yellow": v["n_yellow"],
                           "edge_in_rms": round(v["edge_in_line"]["rms"], 3) if v["edge_in_line"] else None,
                           "edge_in_n": v["edge_in_line"]["n"] if v["edge_in_line"] else None} for k, v in arms.items()}
    return {"out": out, "arms": arms, "best": best, "X": X, "bis": bis}

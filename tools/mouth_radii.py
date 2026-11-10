"""Measure every side-street mouth corner's curb-return RADIUS on NAIP 2023 (ledger 0086 fix, Sand Creek 0.2.7).

    python tools/mouth_radii.py <project-dir> --naip <naip_2023_sc_z18.jpg> [--prefix grid_] --out <json> [--sheet <png>]

Kevin, 2026-11-07, on Sand Creek's grid mouths: "Doesn't connect, floats"; the standing rule "I just want real". The fix
(route.mouth_returns, tools/mouth_returns_blend.py) rounds each corner with a circle tangent to the host's and the
street's pavement edges; this measures that circle's radius off the imagery, corner by corner, so the return is the real
corner's and not a number picked for all of them.

THE MEASUREMENT, per corner (a mouth has two: the street's two edges; key "<piece>|<end>|<e>", e = +1 the street's left
edge in its own point order, -1 its right, the CURB side numbering tools/mouth_weld.py uses):

  1. The BUILT corner frame (the workshop's data: the host's line and the piece's smoothed line with their widths, as
     tools/verify_mouths.py / tools/mouth_survey.py read them): K, where the street's edge line meets the host's edge
     line; a = along the host's edge away from the street; n = out of the host; the street edge's outward direction b
     and the ground wedge's angle phi between a and b.
  2. ROAD GRAY: the median of the NAIP gray on the two pavements beside the corner (the host 5-25 m along a, 1 m in
     from its edge to the middle of its half; the street 5-20 m out, 1 m in from its edge to its centre); a pixel is
     ROAD when it is within max(BAND_MIN, BAND_K x the robust spread) of it.
  3. THE REAL EDGES: along each leg, EDGE_U from K, the straight line parallel to the built edge (offset in EDGE_OFF)
     that best separates the pavement from its side: the gray CONTRAST_M inside it against CONTRAST_M outside, scored
     only where the inside reads ROAD (the arc's own rule, below). Its offset from the built edge is dh (host) / ds
     (street); a leg whose best line is under CONTRAST_MIN or PROM_MIN is not found (built edge kept, flagged).
  4. THE RADIUS: for every R in R_GRID, the circle tangent to both real edges; along the middle ARC_MID of its arc
     the gray CONTRAST_M inside (toward the corner K') against CONTRAST_M outside, where the inside reads ROAD: the
     score is the mean contrast x the share of the arc whose inside is ROAD. The real return is the arc that separates
     the pavement from what is beside it (a curb's concrete, a lot's gravel, a verge): the score's peak. Reported: the
     peak's contrast, its prominence over the grid's median score, the edges' offsets, contrasts and prominences.
  5. ACCEPTED when the contrast is >= CONTRAST_MIN and the prominence >= PROM_MIN, both legs' edges were found, and R
     is inside the grid's ends; otherwise the corner is NOT MEASURED and says why (a paved lot running on from the
     corner, a leg with no edge, a fit at the grid's end). tools/mouth_returns_blend.py builds a not-measured corner at the median of the
     measured corners on the same host (else of all measured corners) and says so; no number is invented per corner.

NAIP: tracks/sand-creek/source/naip_2023_sc_z18.jpg, the 2023 0.3 m scene (co_m_3910409_se_13_030_20230925) served as
web-mercator z18 tiles, 0.46 m a pixel at Sand Creek's latitude, read bilinear through tools/naip_edge.Naip (the track
frame, x = E, z = N). Numbers marked [invented] are sampling choices, in fleet/GATES-CHANGELOG.md (2026-11-07, 0086).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import naip_edge as ne  # noqa: E402
import verify_mouths as vm  # noqa: E402

BAND_MIN = 16.0        # [invented] the road band's half-width floor (8-bit gray)
BAND_K = 2.5           # [invented] ... or this many robust spreads (1.4826 MAD) of the road's own gray
EDGE_U = (12.0, 30.0)  # [invented] each leg's straight edge is fitted this far from K (past most returns)
EDGE_OFF = (-3.0, 8.0) # [invented] ... searched this far either side of the built edge (+ = outward)
R_GRID = [0.5 + 0.25 * k for k in range(79)]      # 0.5 .. 20.0 m
ARC_MID = 0.7          # [invented] the middle share of each candidate arc that is scored
CONTRAST_M = 0.7       # [invented] inside / outside sample offset across the arc (1.5 NAIP px)
CONTRAST_MIN = 12.0    # [invented] the winning arc separates the road from its side by at least this (8-bit gray)
PROM_MIN = 1.4         # [invented] ... and its score stands this far over the grid's median score


def _unit(x, z):
    L = math.hypot(x, z)
    return (x / L, z / L) if L > 1e-12 else (0.0, 0.0)


def corner_frames(mo, conns, local):
    """the mouth's two corners in the built frame: [{e, K, a, n, b, phi, hw, sw, side}] (plan, engine x / z)"""
    piece, end = vm._find_piece(mo, conns)
    if piece is None:
        return None, "no piece"
    if mo["host"] == "MAINLINE":
        hp = vm.Path2(local["points_xyz_m"], local["widths_m"])
    else:
        hc = next(c for c in conns if c["name"] == mo["host"])
        hp = vm.Path2(hc["points_xyz_m"], hc["widths_m"])
    pp = vm.Path2(vm.smooth_xz([tuple(q) for q in piece["points_xyz_m"]]), piece["widths_m"])
    plen = pp.s[-1]
    sd = (lambda u: u) if end == "start" else (lambda u: plen - u)
    sgn = 1.0 if end == "start" else -1.0                       # the piece's own tangent, signed away from the host
    cx, _cy, cz = mo["cut_xyz"]
    _d, c0, _l = hp.project(cx, cz)
    q10 = pp.point(sd(min(10.0, plen)), 0.0)
    side = 1 if hp.project(q10[0], q10[1])[2] >= 0 else -1
    out = []
    for e in (1, -1):
        # the street edge line, fitted on 6-18 m from the cut (past the weld's re-spread, inside a short piece)
        us = [u for u in np.arange(6.0, min(18.0, plen - 0.5), 1.0)]
        if len(us) < 3:
            us = list(np.linspace(min(2.0, plen * 0.3), plen * 0.9, 5))
        P = []
        for u in us:
            (x0, z0), (tx, tz), (nx, nz), w = pp.frame(sd(u))
            P.append((x0 + nx * e * w / 2.0, z0 + nz * e * w / 2.0))
        P = np.array(P)
        bdir = _unit(*(P[-1] - P[0]))                          # away from the host
        # K: march from P[0] back along -bdir until the host edge (the mouth side) is crossed
        K = None
        prev = None
        for k in range(0, 600):
            t = 0.1 * k
            x, z = P[0][0] - bdir[0] * t, P[0][1] - bdir[1] * t
            _dd, sh, lat = hp.project(x, z)
            g = side * lat - hp.frame(sh)[3] / 2.0
            if prev is not None and (prev[0] > 0) != (g > 0):
                f = prev[0] / (prev[0] - g)
                K = (prev[1][0] + (x - prev[1][0]) * f, prev[1][1] + (z - prev[1][1]) * f)
                break
            prev = (g, (x, z))
        if K is None:
            return None, f"edge {e:+d} never meets the host edge"
        _dd, sK, _lat = hp.project(*K)
        (hx, hz), (htx, htz), (hnx, hnz), hw = hp.frame(sK)
        n = (hnx * side, hnz * side)                            # out of the host
        # the street's outward lateral at this edge: from its centre line to the edge
        (x0, z0), _t, (pnx, pnz), sw = pp.frame(sd(us[0]))
        ne_ = (pnx * e, pnz * e)
        a = (htx, htz) if htx * ne_[0] + htz * ne_[1] > 0 else (-htx, -htz)
        cphi = max(-1.0, min(1.0, a[0] * bdir[0] + a[1] * bdir[1]))
        out.append({"e": e, "K": K, "a": a, "n": n, "b": bdir, "nb": ne_, "phi": math.degrees(math.acos(cphi)),
                    "hw": hw, "sw": sw, "side": side, "sK": sK})
    return out, None


def measure_corner(N, cf):
    K, a, n, b, nb = cf["K"], cf["a"], cf["n"], cf["b"], cf["nb"]
    rec = {"phi_deg": round(cf["phi"], 2), "K": [round(K[0], 2), round(K[1], 2)]}
    # 2. the road's gray
    S = []
    for u in np.arange(5.0, 25.0, 0.5):
        for d in np.arange(1.0, max(1.5, cf["hw"] / 2.0), 0.5):
            S.append((K[0] + a[0] * u - n[0] * d, K[1] + a[1] * u - n[1] * d))
        for d in np.arange(1.0, max(1.5, cf["sw"] / 2.0), 0.5):
            S.append((K[0] + b[0] * u - nb[0] * d - a[0] * 0.0, K[1] + b[1] * u - nb[1] * d))
    S = np.array(S)
    g = N.gray(S[:, 0], S[:, 1])
    med = float(np.median(g))
    mad = float(np.median(np.abs(g - med))) * 1.4826
    half = max(BAND_MIN, BAND_K * mad)
    rec["road_gray"] = [round(med, 1), round(half, 1)]

    def road(px, pz):
        return np.abs(N.gray(px, pz) - med) <= half
    # 3. the real edges (offsets from the built ones, + = outward)
    def contrast(px_, pz_, ox, oz):
        """mean |inside - outside| where the inside reads ROAD, x the ROAD share (inside = -o, outside = +o)"""
        gi = N.gray(px_ - ox * CONTRAST_M, pz_ - oz * CONTRAST_M)
        go = N.gray(px_ + ox * CONTRAST_M, pz_ + oz * CONTRAST_M)
        ok_ = np.abs(gi - med) <= half
        return float(np.mean(np.abs(gi - go)[ok_])) * float(np.mean(ok_)) if ok_.any() else 0.0

    def edge_offset(base, along, out):
        """the straight edge parallel to the built one (offset + = outward) that best separates the pavement from its
        side along the whole leg EDGE_U: (offset, contrast, prominence)"""
        us = np.arange(EDGE_U[0], EDGE_U[1] + 1e-9, 0.25)
        offs = np.arange(EDGE_OFF[0], EDGE_OFF[1] + 1e-9, 0.1)
        sc = np.array([contrast(base[0] + along[0] * us + out[0] * d, base[1] + along[1] * us + out[1] * d,
                                out[0], out[1]) for d in offs])
        k = int(np.argmax(sc))
        return float(offs[k]), float(sc[k]), float(sc[k] / max(1e-6, np.median(sc)))
    dh, ch, ph = edge_offset(K, a, n)
    ds, cs, ps = edge_offset(K, b, nb)
    rec["edge_host"] = {"offset_m": round(dh, 2), "contrast": round(ch, 1), "prominence": round(ph, 2)}
    rec["edge_street"] = {"offset_m": round(ds, 2), "contrast": round(cs, 1), "prominence": round(ps, 2)}
    why = []
    # an edge whose best line sits on the search's end is the search running out, not an edge (as R at the grid's end)
    at_end = lambda d: d <= EDGE_OFF[0] + 0.05 or d >= EDGE_OFF[1] - 0.05  # noqa: E731
    if ch < CONTRAST_MIN or ph < PROM_MIN or at_end(dh):
        why.append("host edge not found" + (" (at the search's end)" if at_end(dh) else ""))
        dh = 0.0
    if cs < CONTRAST_MIN or ps < PROM_MIN or at_end(ds):
        why.append("street edge not found" + (" (at the search's end)" if at_end(ds) else ""))
        ds = 0.0
    # the real lines: host p = K + n dh + a t ; street p = K + nb ds + b t ; K' their crossing
    P1 = np.array([K[0] + n[0] * dh, K[1] + n[1] * dh])
    P2 = np.array([K[0] + nb[0] * ds, K[1] + nb[1] * ds])
    A = np.array([[a[0], -b[0]], [a[1], -b[1]]])
    if abs(np.linalg.det(A)) < 1e-6:
        return {**rec, "measured": False, "why": "edges parallel"}
    t = np.linalg.solve(A, P2 - P1)
    Kp = P1 + np.array(a) * t[0]
    phi = math.radians(cf["phi"])
    bis = np.array(_unit(a[0] + b[0], a[1] + b[1]))
    tanh = math.tan(phi / 2.0)
    # 4. the radius: the arc that best SEPARATES the pavement from what is beside it. Per candidate R, the arc's middle
    #    (ARC_MID of it, away from the two tangent points where every candidate arc runs along a straight edge) is
    #    sampled every 0.2 m; at each sample the gray CONTRAST_M inside (toward K') against CONTRAST_M outside: the
    #    score is the mean |inside - outside| over the samples whose inside reads ROAD. The best R is the score's peak;
    #    "prominence" is that peak over the median score of the grid.
    scores = []
    for R in R_GRID:
        O = Kp + bis * (R / math.sin(phi / 2.0))
        tH = R / tanh
        Ta = Kp + np.array(a) * tH
        Tb = Kp + np.array(b) * tH
        a0 = math.atan2(Ta[1] - O[1], Ta[0] - O[0])
        a1 = math.atan2(Tb[1] - O[1], Tb[0] - O[0])
        da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        n_s = max(5, int(abs(da) * R / 0.2))
        f = np.linspace(0.5 - ARC_MID / 2.0, 0.5 + ARC_MID / 2.0, n_s)
        ang = a0 + da * f
        cx_, cz_ = np.cos(ang), np.sin(ang)
        px_, pz_ = O[0] + R * cx_, O[1] + R * cz_
        gi = N.gray(px_ + cx_ * CONTRAST_M, pz_ + cz_ * CONTRAST_M)      # radial outward from O = toward K'
        go = N.gray(px_ - cx_ * CONTRAST_M, pz_ - cz_ * CONTRAST_M)
        ok_ = np.abs(gi - med) <= half
        sc = float(np.mean(np.abs(gi - go)[ok_])) * float(np.mean(ok_)) if ok_.any() else 0.0
        scores.append(sc)
    scores = np.array(scores)
    k = int(np.argmax(scores))
    R = R_GRID[k]
    prom = float(scores[k] / max(1e-6, np.median(scores)))
    rec.update({"radius_m": R, "contrast": round(float(scores[k]), 1), "prominence": round(prom, 2),
                "Kreal": [round(float(Kp[0]), 2), round(float(Kp[1]), 2)]})
    if scores[k] < CONTRAST_MIN:
        why.append(f"contrast {scores[k]:.1f} < {CONTRAST_MIN}")
    if prom < PROM_MIN:
        why.append(f"prominence {prom:.2f} < {PROM_MIN}")
    if R <= R_GRID[0] or R >= R_GRID[-1]:
        why.append(f"fit at the grid's end ({R} m)")
    rec["measured"] = not why
    if why:
        rec["why"] = "; ".join(why)
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--naip", required=True)
    ap.add_argument("--georef", default=str(ne.NAIP_GEOREF))
    ap.add_argument("--prefix", action="append", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--sheet", default=None)
    a = ap.parse_args(argv)
    proj = Path(a.project)
    data = proj / "data"
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    N = ne.Naip(cfg["origin"], image=a.naip, georef=a.georef)
    mouths = json.loads((data / "mouths.json").read_text(encoding="utf-8"))["mouths"]
    conns = json.loads((data / "connectors.local.json").read_text(encoding="utf-8"))["connectors"]
    local = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    pre = a.prefix or ["grid_"]
    corners = {}
    tiles = []
    for mo in mouths:
        if not any(str(mo.get("piece") or mo["connector"]).startswith(p) for p in pre):
            continue
        cfs, err = corner_frames(mo, conns, local)
        if cfs is None:
            print(f"[radii] {mo['piece']}({mo['end']}): {err}")
            continue
        for cf in cfs:
            key = f"{mo['piece']}|{mo['end']}|{cf['e']:+d}"
            r = measure_corner(N, cf)
            r["host"] = mo["host"]
            corners[key] = r
            tiles.append((key, cf, r))
            print(f"[radii] {key} -> {mo['host']}: phi {r['phi_deg']} deg, R {r.get('radius_m')} m, contrast "
                  f"{r.get('contrast')} x{r.get('prominence')}, edges host {r['edge_host']} street {r['edge_street']}"
                  + ("" if r.get("measured") else f"  NOT MEASURED: {r.get('why')}"))
    ok = [r["radius_m"] for r in corners.values() if r.get("measured")]
    res = {"_doc": __doc__.split("\n\n")[0] + " Inputs: " + str(Path(a.naip).name) + " (NAIP 2023, the 0.3 m scene at "
                   "z18, 0.46 m px), the workshop's mouths / connectors / centre line; tools/mouth_radii.py.",
           "naip_item": json.loads(Path(a.georef).read_text(encoding="utf-8")).get("item"),
           "params": {"BAND_MIN": BAND_MIN, "BAND_K": BAND_K, "EDGE_U": EDGE_U,
                      "EDGE_OFF": EDGE_OFF,"R_GRID": [R_GRID[0], R_GRID[-1], 0.25], "ARC_MID": ARC_MID,
                      "CONTRAST_M": CONTRAST_M, "CONTRAST_MIN": CONTRAST_MIN, "PROM_MIN": PROM_MIN},
           "summary": {"corners": len(corners), "measured": len(ok),
                       "median_m": float(np.median(ok)) if ok else None,
                       "p10_p90_m": [float(np.percentile(ok, 10)), float(np.percentile(ok, 90))] if ok else None},
           "corners": corners}
    Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(f"[radii] {len(ok)} of {len(corners)} corners measured; median {res['summary']['median_m']} m, p10/p90 "
          f"{res['summary']['p10_p90_m']} -> {a.out}")
    if a.sheet:
        contact_sheet(N, tiles, Path(a.sheet))
    return 0


def contact_sheet(N, tiles, out, half=18.0, res=0.2, cols=12):
    """every corner: NAIP gray round K', the fitted fillet (green: measured, red: not), the real edges (yellow)"""
    from PIL import Image, ImageDraw
    px = int(2 * half / res)
    rows = int(math.ceil(len(tiles) / cols))
    sheet = Image.new("RGB", (cols * px, rows * (px + 14)), (0, 0, 0))
    for i, (key, cf, r) in enumerate(tiles):
        Kp = r.get("Kreal") or r["K"]
        xs = np.arange(Kp[0] - half, Kp[0] + half, res)
        zs = np.arange(Kp[1] + half, Kp[1] - half, -res)
        X, Z = np.meshgrid(xs, zs)
        g = N.gray(X.ravel(), Z.ravel()).reshape(X.shape)
        im = Image.fromarray(np.clip(g, 0, 255).astype(np.uint8)).convert("RGB")
        d = ImageDraw.Draw(im)

        def P(x, z):
            return ((x - (Kp[0] - half)) / res, ((Kp[1] + half) - z) / res)
        a, b = cf["a"], cf["b"]
        for v in (a, b):
            d.line([P(*Kp), P(Kp[0] + v[0] * 30, Kp[1] + v[1] * 30)], fill=(255, 220, 0), width=1)
        if r.get("radius_m"):
            phi = math.radians(cf["phi"])
            R = r["radius_m"]
            bis = _unit(a[0] + b[0], a[1] + b[1])
            h = R / math.sin(phi / 2.0)
            O = (Kp[0] + bis[0] * h, Kp[1] + bis[1] * h)
            tH = R / math.tan(phi / 2.0)
            Ta = (Kp[0] + a[0] * tH, Kp[1] + a[1] * tH)
            Tb = (Kp[0] + b[0] * tH, Kp[1] + b[1] * tH)
            a0 = math.atan2(Ta[1] - O[1], Ta[0] - O[0])
            a1 = math.atan2(Tb[1] - O[1], Tb[0] - O[0])
            da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
            pts = [P(O[0] + R * math.cos(a0 + da * k / 24), O[1] + R * math.sin(a0 + da * k / 24)) for k in range(25)]
            d.line(pts, fill=(0, 255, 0) if r.get("measured") else (255, 0, 0), width=2)
        x0, y0 = (i % cols) * px, (i // cols) * (px + 14)
        sheet.paste(im, (x0, y0))
        ImageDraw.Draw(sheet).text((x0 + 2, y0 + px), f"{key.split('|')[0][5:]} {key.split('|')[2]} R{r.get('radius_m')}",
                                   fill=(255, 255, 255))
    sheet.save(out, quality=85)
    print(f"[radii] contact sheet -> {out}")


if __name__ == "__main__":
    sys.exit(main())

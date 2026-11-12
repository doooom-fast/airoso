"""Re-trace the PPIR infield pieces and the oval's inside edge off NAIP 2023 0.3 m, edge-measured (ledger 0085 Re-trace).

    python tracks/pikes-peak/source/road-course/retrace.py        (needs the NAIP crop: PPIR_NAIP or geo.IMG)

Writes infield_pieces.naip.json (every piece: both edges, centre, width per metre, residuals, inferred stretches, kerb runs,
wear) and inside_edge.naip.json (the oval's inside pavement edge, fitted, with its junction / opening stations).
Method: pieces.py (pieces) and inside_edge() below (the oval). Registration: naip.py applies registration.json.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage
from scipy.interpolate import UnivariateSpline

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import naip  # noqa: E402
import pieces  # noqa: E402


def runs(mask_, s):
    out, a = [], None
    for i, v in enumerate(list(mask_) + [False]):
        if v and a is None:
            a = i
        if not v and a is not None:
            out.append((a, i - 1)); a = None
    return [(float(s[a]), float(s[b])) for a, b in out]


def pct(x):
    x = np.abs(np.asarray(x))
    if not len(x):
        return None
    return {"p50": round(float(np.percentile(x, 50)), 3), "p95": round(float(np.percentile(x, 95)), 3),
            "max": round(float(x.max()), 3), "n": int(len(x))}


def r2(a, nd=2):
    return [[round(float(v), nd) for v in row] for row in a]


RING_SPAN = 18.0     # [invented] how far into the open lot a ring's wear band is looked for


def kerb_trace(E, out_n, s_e):
    """Kerb runs along a fitted edge, read off the strip 0.15-0.6 m outside it (where a kerb starting at the asphalt edge
    lies). Every 0.15 m along the edge: red (fresh or faded kerb red) and white. In 4 m windows: a KERB is red on >= 15 %
    of the strip, or white blocks alternating with gaps (white on 25-80 % of it, >= 0.8 white<->not-white changes per
    metre: the 1 m block rhythm); an EDGE LINE is white on > 80 % with no rhythm. Returns per-station labels."""
    ch = naip.channels()
    n = len(E)
    lab = np.array(["none"] * n, dtype=object)
    if n < 4:
        return lab
    sE = naip.cumlen(E)
    t_ = np.arange(0, sE[-1], 0.15)
    Q = np.c_[np.interp(t_, sE, E[:, 0]), np.interp(t_, sE, E[:, 1])]
    No = np.c_[np.interp(t_, sE, out_n[:, 0]), np.interp(t_, sE, out_n[:, 1])]
    red = np.zeros(len(t_)); wh = np.zeros(len(t_))
    for o in (0.15, 0.3, 0.45, 0.6):
        red = np.maximum(red, naip.sample(ch["red"], Q[:, 0] + o * No[:, 0], Q[:, 1] + o * No[:, 1]))
        wh = np.maximum(wh, naip.sample(ch["white"], Q[:, 0] + o * No[:, 0], Q[:, 1] + o * No[:, 1]))
    rb = red > 0.5; wb = wh > 0.5
    for k in range(n):
        sel = np.abs(t_ - sE[k]) <= 2.0
        if sel.sum() < 10:
            continue
        fr = rb[sel].mean(); fw = wb[sel].mean()
        ch_ = np.abs(np.diff(wb[sel].astype(int))).sum() / 4.0
        if fr >= 0.15 or (0.25 <= fw <= 0.8 and ch_ >= 0.8):
            lab[k] = "kerb"
        elif fw > 0.8:
            lab[k] = "edge_line"
    return lab


def do_piece(name, desc, vias, m, mode="road"):
    G = pieces.guide(m, vias, mode)
    P, L, s, out, offs, prof = pieces.measure_piece(name, G, mode)
    T, L = naip.normals(P)
    rec = {"description": desc, "vias_px": [list(map(int, v)) for v in vias], "kind": mode}
    dd = {}
    for side, sgn in (("left", 1.0), ("right", -1.0)):
        o = out[side]
        ok = o["status"] == "seen"
        if o["sp"] is None or (mode == "ring" and side == "right"):
            # the lot side of a ring: open pavement, no edge; the wear band is read RING_SPAN in from the outer edge
            dd[side] = None
            rec[side] = {"open": "the lot's own pavement (no edge)", "_covered": np.zeros(len(s), bool)}
            continue
        d = o["sp"](s)
        idx0 = np.where(ok)[0]
        d[:idx0[0]] = d[idx0[0]]; d[idx0[-1] + 1:] = d[idx0[-1]]       # no extrapolation: held flat past the seen ends
        res = o["x"][ok] - d[ok]
        idx = np.where(ok)[0]
        lo, hi = idx.min(), idx.max()                      # no extrapolation past the last seen edge
        covered = np.zeros(len(s), bool); covered[lo:hi + 1] = True
        E = P + (sgn * d)[:, None] * L
        # curvature of the fitted edge
        dx = np.gradient(E[:, 0], s); dy = np.gradient(E[:, 1], s)
        kap = np.abs(dx * np.gradient(dy, s) - dy * np.gradient(dx, s)) / np.maximum((dx ** 2 + dy ** 2) ** 1.5, 1e-9)
        st = o["status"]
        reasons = {}
        for why in ("opening", "weak", "shadow", "outlier"):
            rr = runs((st == why) & covered, s)
            rr = [r for r in rr if r[1] - r[0] >= 1.0]
            if rr:
                reasons[why] = [[round(a, 1), round(b, 1)] for a, b in rr]
        # kerbs and edge lines traced ALONG the fitted edge (kerb_trace): the evidence Kevin reads by eye
        lab = np.array(["none"] * len(s), dtype=object)
        lab[covered] = kerb_trace(E[covered], (sgn * L)[covered], s[covered])
        kerb = (lab == "kerb")
        eline = (lab == "edge_line")
        kerb_s = ndimage.binary_closing(kerb, iterations=4)      # gaps < 2 m between kerb sections close
        kruns = []
        for a, b in runs(kerb_s, s):
            if b - a < 3:
                continue
            sel = kerb & (s >= a) & (s <= b)
            w = [o["raw"][k]["kerb"]["width"] for k in np.where(sel)[0]
                 if o["raw"][k] is not None and o["raw"][k]["kerb"] is not None and o["status"][k] == "seen"]
            kruns.append({"s": [round(a, 1), round(b, 1)], "kerb_width_m": round(float(np.median(w)), 2) if w else None})
        dd[side] = d
        rec[side] = {
            "edge_en_m": r2(E[covered][::2]),
            "station_range_m": [round(float(s[lo]), 1), round(float(s[hi]), 1)],
            "seen_fraction": round(float(ok[lo:hi + 1].mean()), 3),
            "residual_m": pct(res),
            "smoothing": round(float(o["ss"]), 4),
            "min_radius_m": round(float(min(pieces.edge_min_radius(E[covered]), 9999)), 1),
            "inferred": reasons,
            "kerb_runs": kruns,
            "edge_evidence": {"kerb": round(float(kerb[lo:hi + 1].mean()), 3), "edge_line": round(float(eline[lo:hi + 1].mean()), 3),
                              "surface_only": round(float((~kerb & ~eline)[lo:hi + 1].mean()), 3)},
            "_covered": covered,
            "_kerb": kerb,
        }
    covl = rec["left"]["_covered"]; covr = rec["right"]["_covered"]
    kerbl = rec["left"].pop("_kerb", np.zeros(len(s), bool)); kerbr = rec["right"].pop("_kerb", np.zeros(len(s), bool))
    both = rec["left"].pop("_covered") & rec["right"].pop("_covered")
    if mode == "ring":
        dl = dd["left"]; dr = RING_SPAN - dl          # wear read from the outer edge RING_SPAN into the lot
        rows_, _ = pieces.wear(P, L, dl, dr)
        # the ring's DRIVEN band: where the darkening exceeds half its section peak, measured from the outer edge
        bw, bin_, bout = [], [], []
        for k, r in enumerate(rows_):
            if r is None:
                bw.append(np.nan); bin_.append(np.nan); bout.append(np.nan); continue
            o_ = np.arange(-dr[k] + 0.5, dl[k] - 0.5 + 1e-9, 0.1)
            E_ = P[k, 0] + o_ * L[k, 0]; N_ = P[k, 1] + o_ * L[k, 1]
            lum = naip.sample(naip.channels()["lum"], E_, N_)
            ref = np.percentile(lum, 80)
            dk = ndimage.gaussian_filter1d(np.clip((ref - lum) / ref, 0, None), 6)
            hi_ = dk >= 0.5 * dk.max()
            i0 = int(np.argmax(dk))
            a_ = i0; b_ = i0
            while a_ > 0 and hi_[a_ - 1]:
                a_ -= 1
            while b_ < len(hi_) - 1 and hi_[b_ + 1]:
                b_ += 1
            bw.append(o_[b_] - o_[a_]); bin_.append(dl[k] - o_[a_]); bout.append(dl[k] - o_[b_])
        bw = np.array(bw); bin_ = np.array(bin_); bout = np.array(bout)
        # the ring's line: the middle of its wear band
        cmid = dl - (bin_ + bout) / 2
        cmid = np.where(np.isfinite(cmid), cmid, np.nanmedian(cmid))
        cmid = ndimage.gaussian_filter1d(cmid, 10)
        C = P + cmid[:, None] * L
        wid = bw
        both = covl.copy()
        rec["wear_band_from_outer_edge_m"] = {"inner_p50": round(float(np.nanmedian(bin_)), 2),
                                              "outer_p50": round(float(np.nanmedian(bout)), 2),
                                              "width_p50": round(float(np.nanmedian(bw)), 2)}
    else:
        dl, dr = dd["left"], dd["right"]
        C = P + ((dl - dr) / 2)[:, None] * L
        # the midline, smoothed over 2 m of its own length: where the guide's normals fan across a tight bend the raw
        # midline can curl on itself by a metre or two
        C = naip.resample(C, 0.25)
        C = np.c_[ndimage.gaussian_filter1d(C[:, 0], 8, mode="nearest"), ndimage.gaussian_filter1d(C[:, 1], 8, mode="nearest")]
        C = naip.resample(C, pieces.STEP)
        if len(C) != len(P):
            C = np.c_[np.interp(np.linspace(0, 1, len(P)), np.linspace(0, 1, len(C)), C[:, 0]),
                      np.interp(np.linspace(0, 1, len(P)), np.linspace(0, 1, len(C)), C[:, 1])]
        wid = dl + dr
    sc = naip.cumlen(C)
    # per metre
    sm = np.arange(0, sc[-1] + 1e-9, 1.0)
    Cm = np.c_[np.interp(sm, sc, C[:, 0]), np.interp(sm, sc, C[:, 1])]
    Wm = np.interp(sm, sc, np.where(both, wid, np.nan))
    rec["length_m"] = round(float(sc[-1]), 1)
    rec["centre_en_m"] = r2(Cm)
    rec["width_m_per_metre"] = [None if not np.isfinite(w) else round(float(w), 2) for w in Wm]
    wv = Wm[np.isfinite(Wm)]
    rec["width_m"] = {"min": round(float(wv.min()), 2), "p50": round(float(np.median(wv)), 2), "max": round(float(wv.max()), 2)} if len(wv) else None
    px, py = naip.en_to_px(Cm[:, 0], Cm[:, 1])
    rec["centre_px"] = r2(np.c_[px, py][::4], 1)
    # wear
    rows, bins = pieces.wear(P, L, dl, dr)
    pk = np.array([r["peak"] if r else np.nan for r in rows])
    uu = np.array([r["u"] if r else np.nan for r in rows])
    B = np.array([b for b in bins if b is not None])
    rec["wear"] = {
        "index": round(float(np.nanmedian(pk)), 4),
        "p90": round(float(np.nanpercentile(pk, 90)), 4),
        "profile_u0_right_to_u1_left": [round(float(v), 4) for v in np.nanmedian(B, axis=0)],
        "band_u_per_2m": [None if not np.isfinite(v) else round(float(v), 2) for v in uu[::4]],
        "band_peak_per_2m": [None if not np.isfinite(v) else round(float(v), 3) for v in pk[::4]],
    }
    # curvature of the centre (signed, + = left turn in the piece's direction) for the direction test
    T2, _ = naip.normals(C)
    hd = np.unwrap(np.arctan2(T2[:, 1], T2[:, 0]))
    kc = np.gradient(hd, naip.cumlen(C))
    kc = ndimage.gaussian_filter1d(kc, 4)
    rec["_internal"] = dict(P=P, L=L, s=s, dl=dl, dr=dr, C=C, k=kc, band_off=np.array([r["off"] if r else np.nan for r in rows]), peak=pk,
                           xl=out["left"]["x"], stl=out["left"]["status"], xr=out["right"]["x"], str_=out["right"]["status"], mode=mode,
                           kl=kerbl, kr=kerbr,
                           kol=np.array([np.nan if (r is None or r["kerb"] is None) else r["kerb"]["outer"] for r in out["left"]["raw"]]) if True else None,
                           kor=np.array([np.nan if (r is None or r["kerb"] is None) else r["kerb"]["outer"] for r in out["right"]["raw"]]),
                           band_u=uu, covl=covl, covr=covr)
    return rec


def corner_direction(rec):
    """Per corner (|k| > 1/60 m over >= 8 m), the wear band's closest approach to the corner's INSIDE edge (its apex)
    against the corner's curvature-weighted middle. A late apex is the rubber of a car travelling that way; the shift
    is reported in the piece's own direction (+ = apex later = the piece's direction)."""
    I = rec["_internal"]
    s, k, dl, dr, off, pk = I["s"], I["k"], I["dl"], I["dr"], I["band_off"], I["peak"]
    cs = []
    on = np.abs(k) > 1 / 60.0
    for a, b in runs(on, np.arange(len(s))):
        a, b = int(a), int(b)
        if s[b] - s[a] < 8:
            continue
        sl = slice(a, b + 1)
        sign = np.sign(np.median(k[sl]))
        inside = dl[sl] if sign > 0 else dr[sl]
        o = off[sl] if sign > 0 else -off[sl]
        dist = inside - o                       # band distance from the inside edge
        good = np.isfinite(dist) & (pk[sl] > 0.03)
        if good.sum() < 5:
            continue
        w = np.abs(k[sl])
        mid = float(np.sum(s[sl] * w) / np.sum(w))
        dsm = ndimage.gaussian_filter1d(np.where(good, dist, np.nanmax(dist[good])), 2)
        ap = float(s[sl][np.argmin(dsm)])
        cs.append({"s": [round(float(s[a]), 1), round(float(s[b]), 1)], "turn": "left" if sign > 0 else "right",
                   "radius_m": round(float(1 / np.median(w)), 1), "apex_minus_middle_m": round(ap - mid, 1),
                   "band_to_inside_at_apex_m": round(float(np.min(dsm)), 2),
                   "band_peak": round(float(np.nanmedian(pk[sl])), 3)})
    return cs


def inside_edge(m):
    """The oval's inside pavement edge, every 1 m of the port's line. Search inward along the line's left normal from
    the lidar wall face; edge = the first pavement-score 0.5 crossing that stays below 0.5 for >= 2 m, sub-pixel.
    Stations with no such crossing before 45 m, or one > 3 m beyond the running median, are JUNCTION / OPENING (other
    pavement continues: the pit lane, a service road, an infield junction); the fitted curve bridges them, never follows."""
    ov = naip.oval_line()
    line = ov["line"]
    Pc = naip.resample(line, 1.0, closed=True)
    n = len(Pc)
    sP = np.arange(n, dtype=float)
    T, L = naip.normals(Pc, closed=True)
    # the lidar face offset (from the line, outward) at each 1 m station, interpolated on the survey's own stations
    fo = ov["face_off"]
    good = np.isfinite(fo)
    sv = ov["s"]
    sl = naip.cumlen(np.vstack([line, line[:1]]))
    scale = sl[-1] / n
    fo1 = np.interp(sP * scale, sv[good], fo[good], period=sl[-1])
    face = Pc - fo1[:, None] * L
    ch = naip.channels()
    offs = np.arange(0, 45.0, pieces.DS)
    E = Pc[:, 0][:, None] + offs[None, :] * L[:, 0][:, None]
    N = Pc[:, 1][:, None] + offs[None, :] * L[:, 1][:, None]
    pv = naip.sample(ch["pave"], E, N); kb = naip.sample(ch["kerb"], E, N); lm = naip.sample(ch["lum"], E, N)
    raw = [pieces.find_edge(pv[k], kb[k], lm[k], offs) for k in range(n)]
    x = np.array([np.nan if r is None else (r["kerb"]["inner"] if r["kerb"] else r["edge"]) for r in raw])
    status = np.array(["seen" if r is not None else "opening" for r in raw], dtype=object)
    for k, r in enumerate(raw):
        if r is not None and r["strength"] < 0.45:
            status[k] = "weak"
    ok = status == "seen"
    # the racing surface's width from the wall changes slowly (23-26 m, over the banking ramps): against its running
    # median over +-75 m (cyclic), a reading > 1.5 m wider is another pavement joining (opening), > 1.5 m narrower is
    # paint / a car / a patch (outlier)
    yw = x + fo1
    # a seen station with < 5 seen neighbours within +-5 m is a stray crossing in a junction: dropped
    cnt = np.array([ok[(np.arange(k - 5, k + 6)) % n].sum() for k in range(n)])
    status[ok & (cnt < 6)] = "outlier"
    ok = status == "seen"
    for _ in range(4):
        idx = np.where(ok)[0]
        med = np.empty(n)
        for k in range(n):
            dd_ = np.abs(((idx - k) + n // 2) % n - n // 2)
            sel = idx[dd_ <= 75]
            med[k] = np.median(yw[sel]) if len(sel) >= 10 else np.nan
        bad = ok & np.isfinite(med) & (np.abs(yw - med) > 1.5)
        status[bad & (yw > med)] = "opening"
        status[bad & (yw <= med)] = "outlier"
        ok = status == "seen"
    # periodic smoothing spline of the wall-face-to-edge width: robust (points > max(0.35 m, 3 MAD-sigma) off it
    # drop to 'outlier'), then smoothing doubled (at most 8x) until the edge's own radius is >= 20 m [invented]
    for _ in range(6):
        ext = np.r_[sP[ok] - n, sP[ok], sP[ok] + n]
        y = x + fo1                       # fitted as the WIDTH from the lidar wall face: smooth, so gaps bridge flat
        xe = np.r_[y[ok], y[ok], y[ok]]
        ss = 0.12 ** 2 * len(xe)
        sp = UnivariateSpline(ext, xe, k=3, s=ss)
        r = y - sp(sP)
        sig = 1.4826 * np.median(np.abs(r[ok]))
        bad = ok & (np.abs(r) > max(0.35, 3 * sig))
        if not bad.any():
            break
        status[bad & (r > 0)] = "opening"
        status[bad & (r <= 0)] = "outlier"
        ok = status == "seen"
    for _ in range(4):
        sp = UnivariateSpline(ext, xe, k=3, s=ss)
        d = sp(sP) - fo1
        Ed = Pc + d[:, None] * L
        rmin = pieces.edge_min_radius(np.vstack([Ed, Ed[:20]]))
        if rmin >= 20.0:
            break
        ss *= 2
    # a gap (no seen edge) longer than 10 m is bridged STRAIGHT in width between the fitted widths at its two ends:
    # the spline alone wanders across a 200 m gap
    wfit = d + fo1
    ii = np.where(ok)[0]
    for k in range(len(ii)):
        a_, b_ = ii[k], ii[(k + 1) % len(ii)]
        gap = (b_ - a_) % n
        if gap > 10:
            for j in range(1, gap):
                q = (a_ + j) % n
                wfit[q] = wfit[a_] + (wfit[b_] - wfit[a_]) * j / gap
    d = wfit - fo1
    Ed = Pc + d[:, None] * L
    rmin = pieces.edge_min_radius(np.vstack([Ed, Ed[:20]]))
    kap = np.array([1 / max(rmin, 1e-9)])
    res = x[ok] - d[ok]
    width = d + fo1                      # inside edge to the lidar wall face
    # the APRON LINE: the painted white line nearest the inside edge (0.8-10 m out from it, toward the wall): the white
    # score's strongest peak there, kept where it is >= 0.5; sub-sample by a parabola. Racing surface = wall face to it.
    wsc = naip.channels()["white"]
    from scipy import ndimage as _nd
    wsm = _nd.gaussian_filter(wsc, 0.6)
    oo = np.arange(0.8, 10.0, 0.1)
    apron = np.full(n, np.nan)
    for k in range(n):
        Eo = Ed[k, 0] - oo * L[k, 0]; No = Ed[k, 1] - oo * L[k, 1]
        v = naip.sample(wsm, Eo, No)
        i = int(np.argmax(v))
        if v[i] >= 0.5 and 0 < i < len(v) - 1:
            den = v[i - 1] - 2 * v[i] + v[i + 1]
            fr = 0.5 * (v[i - 1] - v[i + 1]) / den if den < -1e-9 else 0.0
            apron[k] = oo[i] + np.clip(fr, -0.5, 0.5) * 0.1
    # keep only readings consistent along the lap (a painted line is continuous): within 0.6 m of the 31 m running median
    good = np.isfinite(apron)
    med = pieces.running_median(np.where(good, apron, 0), good, w=31)
    apron[good & (np.abs(apron - med) > 0.6)] = np.nan
    return dict(Pc=Pc, L=L, s=sP * scale, d=d, x=x, status=status, ok=ok, res=res, face=face, width=width, edge=Ed,
                ss=ss, kmax=float(kap.max()), raw=raw, apron=apron)


SECTIONS = [("front stretch (incl. its dogleg)", -169, 198), ("turns 1-2", 198, 660), ("back stretch", 660, 1032),
            ("turns 3-4", 1032, 1497)]   # bounds: |bank| crosses 15 % (ledger 0085 Part 1); the front wraps past s 0


def write_inside(ie):
    s = ie["s"]; lap = float(s[-1] + (s[1] - s[0]))
    st = ie["status"]
    ok = ie["ok"]
    lab = np.where(ok, "seen", np.where(st == "opening", "junction_or_opening", "inferred_" + st.astype(str)))
    rows = []
    for k in range(len(s)):
        rows.append({"s": round(float(s[k]), 1),
                     "edge_en_m": [round(float(ie["edge"][k, 0]), 2), round(float(ie["edge"][k, 1]), 2)],
                     "edge_from_line_m": round(float(ie["d"][k]), 2),
                     "wall_face_to_edge_m": round(float(ie["width"][k]), 2),
                     "apron_line_from_edge_m": None if not np.isfinite(ie["apron"][k]) else round(float(ie["apron"][k]), 2),
                     "label": str(lab[k])})
    def sec(lo, hi):
        sw = np.where(s > lap / 2, s - lap, s) if lo < 0 else s
        sel = (sw >= lo) & (sw < hi)
        w = ie["width"][sel]
        ap = ie["apron"][sel & ok]
        ap = ap[np.isfinite(ap)]
        ws = ie["width"][sel & ok]
        return {"s": [round(lo % lap, 1), hi], "wall_face_to_inside_edge_m": {"min": round(float(ws.min()), 2), "p50": round(float(np.median(ws)), 2),
                                                                  "max": round(float(ws.max()), 2), "of": "seen stations only"},
                "seen_fraction": round(float(ok[sel].mean()), 3),
                "apron_line_from_edge_m": None if len(ap) < 10 else {"p10": round(float(np.percentile(ap, 10)), 2), "p50": round(float(np.median(ap)), 2),
                                                                      "p90": round(float(np.percentile(ap, 90)), 2), "stations": int(len(ap))},
                "wall_face_to_apron_line_m": None if len(ap) < 10 else round(float(np.median(ws[np.isfinite(ie["apron"][sel & ok])] - ap)), 2)}
    open_runs = [[round(a, 1), round(b, 1)] for a, b in runs(lab == "junction_or_opening", s) if b - a >= 2]
    inf_runs = [[round(a, 1), round(b, 1)] for a, b in runs(np.char.startswith(lab.astype(str), "inferred"), s) if b - a >= 2]
    summ = {"_doc": ("The oval's INSIDE pavement edge off NAIP 2023 0.3 m (retrace.py inside_edge(): per 1 m station of the "
                     "port's line, inward along its left normal, the first sustained pavement-score fall, sub-pixel; a "
                     "periodic smoothing spline through the seen stations, curvature >= 1/20 m; junctions and openings "
                     "BRIDGED by it, never followed). Width = that edge to the 2018 lidar wall face (wall_right.json). "
                     "Replaces the zig-zag first-non-pavement-run read (inside_edge.eyeball.json)."),
            "stations": int(len(s)), "seen": int(ok.sum()),
            "residual_m": pct(ie["res"]),
            "smoothing": round(float(ie["ss"]), 3), "min_radius_m": round(float(1 / max(ie["kmax"], 1e-9)), 1),
            "junction_or_opening_runs_s": open_runs, "inferred_runs_s": inf_runs,
            "sections": {name: sec(lo, hi) for name, lo, hi in SECTIONS},
            "published": "60-71 ft (18.3-21.6 m) variable-width racing surface (racingcircuits.info), plus an apron"}
    allw = ie["width"]
    summ["wall_face_to_inside_edge_m"] = {"min": round(float(allw.min()), 2), "p50": round(float(np.median(allw)), 2),
                                          "max": round(float(allw.max()), 2)}
    (HERE / "inside_edge.naip.json").write_text(json.dumps({"summary": summ, "rows": rows}, indent=0))
    print(json.dumps(summ, indent=1))


def main():
    m = pieces.mask()
    out = {"_doc": ("PPIR infield pavement, edge-measured off NAIP 2023 0.3 m (ledger 0085 Re-trace; retrace.py, pieces.py). "
                    "ENU metres about tracks/pikes-peak/data/centerline.local.json's origin, NAIP registration removed "
                    "(registration.json). Each piece's direction is its via order; 'left'/'right' face that direction. "
                    "edge_en_m every 1 m between its first and last seen edge point; centre_en_m and width every 1 m."),
           "registration": json.loads((HERE / "registration.json").read_text())["shift_en_m"]
           if json.loads((HERE / "registration.json").read_text()).get("apply") else [0, 0],
           "pieces": {}}
    internals = {}
    for name, spec in pieces.PIECES.items():
        desc, vias = spec[0], spec[1]
        mode = spec[2] if len(spec) > 2 else "road"
        try:
            rec = do_piece(name, desc, vias, m, mode)
        except SystemExit as e:
            print("FAILED", name, e); continue
        rec["wear"]["corners"] = corner_direction(rec)
        internals[name] = rec.pop("_internal")
        out["pieces"][name] = rec
        print(f"{name:10s} {rec['length_m']:6.1f} m  width {rec['width_m']}  L res {rec['left']['residual_m']}  "
              f"R res {rec['right'].get('residual_m')}  wear {rec['wear']['index']}")
    (HERE / "infield_pieces.naip.json").write_text(json.dumps(out, indent=0))
    ie = inside_edge(m)
    write_inside(ie)
    naip.CACHE.mkdir(parents=True, exist_ok=True)
    import pickle
    pickle.dump(internals, open(naip.CACHE / "internals.pkl", "wb"))
    pickle.dump({k: v for k, v in ie.items() if k != "raw"}, open(naip.CACHE / "inside.pkl", "wb"))
    return out, ie


if __name__ == "__main__":
    main()

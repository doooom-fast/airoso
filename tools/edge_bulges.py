"""Bulges in a built road's edges, any track (ledger 0103; Kevin 2026-11-24: "Look for primarily bulges during otherwise
smooth curves and straights" / "It's like flying a camera would see it faster"). A report, not a gate.

    python tools/edge_bulges.py <track dir> --workshop <workshop>      the built road: <workshop>/data/track.obj
    python tools/edge_bulges.py <track dir> --line <centerline.json>   a line + widths (the intake's, before a build)
        [--out <report.json>] [--png <prefix>]

The edges: per side, the lane edge's offset e(s) off the lap line every 0.5 m (built: the nearest crossing of the 1ROAD
boundary along the line's normal, the line = data/finished_centerline.json in the OBJ's frame; --line: +-width / 2).
tools/edge_design.py lays each series out (its swells and pinches narrower than 200 m taken out, steps and tapers kept)
and finds every excursion from that layout (per side, and on the width); each is judged against the measured edge: the track's lidar edges where they cover it, its edge evidence elsewhere.
A second signal, the edge's own plan curvature against the one a parallel offset of the line would have: its 2-30 m
wobble per 100 m and the flips (the edge turning the other way while the line does not).
The track's track.config.json "edge_bulges" block (all optional): "evidence" (points [E, N, src, ...] in the line's frame),
"lidar_edges" (an edges_curves.py read: stations {s, left.u_m, right.u_m}), both paths in the track dir; "skip" [[s0, s1]]
(stretches the report counts apart, e.g. a banked bowl built from its own section); the spans and tapers of every
lm_intake.edge_retrace record count apart as well (the retrace re-traces them to the measured edge).
The PNG (PIL): the lap in rows of 400 m, each side's e(s) across with the offset exaggerated, the measured 5 m medians,
the bulges shaded (red = ours, green = real, grey = unmeasured).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import edge_design as ED  # noqa: E402

DS = 0.5
CELL = 3.0
REACH = 25.0
KAPPA_SMOOTH_M = 4.0   # [invented] the edge curvature's derivative chord
FLIP_KAPPA = 1 / 2000  # [invented] a line this straight or straighter has no turn to flip against


def _road_boundary(obj: Path):
    verts, tris, road = [], [], False
    with open(obj, encoding="utf-8") as f:
        for ln in f:
            if ln.startswith("v "):
                p = ln.split()
                verts.append((float(p[1]), float(p[3])))
            elif ln.startswith("o "):
                road = ln[2:].strip().upper().startswith("1ROAD")
            elif road and ln.startswith("f "):
                idx = [int(t.split("/")[0]) - 1 for t in ln.split()[1:]]
                tris.extend((idx[0], idx[k], idx[k + 1]) for k in range(1, len(idx) - 1))
    V = np.array(verts)
    _, weld = np.unique(np.round(V / 0.002).astype(np.int64), axis=0, return_inverse=True)
    weld = weld.ravel()
    rep = {}
    for i, w in enumerate(weld):
        rep.setdefault(w, i)
    cnt = defaultdict(int)
    for a, b, c in tris:
        for e0, e1 in ((a, b), (b, c), (c, a)):
            u, v = weld[e0], weld[e1]
            if u != v:
                cnt[(min(u, v), max(u, v))] += 1
    segs = np.array([(V[rep[a]], V[rep[b]]) for (a, b), c in cnt.items() if c == 1])
    return segs, V


def _cast(segs, x, z, nx, nz):
    h = defaultdict(list)
    for i, (a, b) in enumerate(segs):
        for gx in range(int(min(a[0], b[0]) // CELL), int(max(a[0], b[0]) // CELL) + 1):
            for gz in range(int(min(a[1], b[1]) // CELL), int(max(a[1], b[1]) // CELL) + 1):
                h[(gx, gz)].append(i)
    u = np.full((2, len(x)), np.nan)
    for k in range(len(x)):
        for j, sd in enumerate((1.0, -1.0)):
            dx, dz = sd * nx[k], sd * nz[k]
            cand = set()
            for q in np.arange(0, REACH + CELL, CELL / 2):
                gx, gz = int((x[k] + dx * q) // CELL), int((z[k] + dz * q) // CELL)
                for ax in (-1, 0, 1):
                    for az in (-1, 0, 1):
                        cand.update(h.get((gx + ax, gz + az), ()))
            best = None
            for i in cand:
                (ax_, az_), (bx_, bz_) = segs[i]
                ex, ez = bx_ - ax_, bz_ - az_
                den = dx * ez - dz * ex
                if abs(den) < 1e-12:
                    continue
                t = ((ax_ - x[k]) * ez - (az_ - z[k]) * ex) / den
                w = ((ax_ - x[k]) * dz - (az_ - z[k]) * dx) / den
                if 0.05 < t <= REACH and -1e-9 <= w <= 1 + 1e-9 and (best is None or t < best):
                    best = t
            if best is not None:
                u[j, k] = best
    return u


def _frame(P):
    E = np.c_[P[:, 0], P[:, 1]]
    seg = np.r_[0, np.cumsum(np.hypot(*np.diff(E, axis=0).T))]
    s = np.arange(0, seg[-1], DS)
    x, z = np.interp(s, seg, E[:, 0]), np.interp(s, seg, E[:, 1])
    tx, tz = np.gradient(x), np.gradient(z)
    tn = np.hypot(tx, tz)
    return s, x, z, -tz / tn, tx / tn, seg


def _fill(y):
    y = y.copy()
    ok = np.isfinite(y)
    y[~ok] = np.interp(np.flatnonzero(~ok), np.flatnonzero(ok), y[ok])
    return y


def _curv(x, z):
    h = max(int(round(KAPPA_SMOOTH_M / 2 / DS)), 1)
    dx, dz = (np.roll(x, -h) - np.roll(x, h)) / (2 * h * DS), (np.roll(z, -h) - np.roll(z, h)) / (2 * h * DS)
    ddx, ddz = (np.roll(dx, -h) - np.roll(dx, h)) / (2 * h * DS), (np.roll(dz, -h) - np.roll(dz, h)) / (2 * h * DS)
    return (dx * ddz - dz * ddx) / np.maximum((dx * dx + dz * dz) ** 1.5, 1e-9)


def _band(y, lo, hi):
    F = np.fft.rfft(y - y.mean())
    f = np.fft.rfftfreq(len(y), DS)
    with np.errstate(divide="ignore"):
        lam = np.where(f > 0, 1 / f, np.inf)
    F[(lam < lo) | (lam >= hi)] = 0
    return np.fft.irfft(F, len(y))


def measured_series(track: Path, cfg: dict, s, x, z, nx, nz):
    """tools/edge_design.measured on this line: the lidar edges where they cover, the evidence elsewhere"""
    blk = cfg.get("edge_bulges") or {}
    ev = json.loads((track / blk["evidence"]).read_text(encoding="utf-8"))["points"]         if blk.get("evidence") and (track / blk["evidence"]).exists() else []
    lid = json.loads((track / blk["lidar_edges"]).read_text(encoding="utf-8"))         if blk.get("lidar_edges") and (track / blk["lidar_edges"]).exists() else None
    pts = [(float(a), 0.0, float(b)) for a, b in zip(x, z)]
    return ED.measured(pts, [float(v) for v in s], ev, lid)


def analyse(s, e, meas, closed, skip, min_measured):
    """the bulges of one series e(s) every DS, judged; e resampled to ED.SAMPLE_M first"""
    sr, yr = ED.resample(list(map(float, s)), list(map(float, e)))
    lay = ED.layout(yr, closed)
    rows = []
    for b in ED.excursions(yr, lay):
        v, det = ED.verdict(b, sr, yr, lay, meas, min_measured=min_measured)
        s0, s1 = sr[b["i0"]], sr[b["i1"]]
        rows.append({"s": [round(s0, 1), round(s1, 1)], "peak_s": round(sr[b["ipk"]], 1), "amp_m": round(b["amp_m"], 3),
                     "len_m": round(b["len_m"], 1), "dir": "out" if b["dir"] > 0 else "in", "kind": b["kind"],
                     "verdict": v, "skipped": ED._in_spans(s0, s1, skip, sr[-1]), **det,
                     "_i": [b["i0"], b["i1"]]})
    return sr, yr, rows


def run(track: Path, workshop: Path | None, line: Path | None):
    cfg = json.loads((track / "track.config.json").read_text(encoding="utf-8"))
    closed = bool(cfg.get("loop", True))
    skip = [list(map(float, a)) for a in ((cfg.get("edge_bulges") or {}).get("skip") or [])]
    # the stretches an lm_intake.edge_retrace record re-traces to the measured edge (its spans and tapers) count apart too
    er_ = (cfg.get("lm_intake") or {}).get("edge_retrace") or []
    for r_ in (er_ if isinstance(er_, list) else [er_]):
        tp = float(r_.get("taper_m", 60.0))
        skip += [[float(a) - tp, float(b) + tp] for a, b in r_["spans"]]
    if workshop is not None:
        segs, V = _road_boundary(workshop / "data" / "track.obj")
        FC = json.loads((workshop / "data" / "finished_centerline.json").read_text())
        P3 = np.array(FC["points_xyz_m"])
        # the OBJ's frame: the sign of z that puts the line on the road
        probe = P3[:: max(len(P3) // 300, 1)]
        best = None
        for sg in (1.0, -1.0):
            d = np.array([np.min(np.hypot(V[:, 0] - p[0], V[:, 1] - sg * p[2])) for p in probe[:60]])
            if best is None or np.median(d) < best[0]:
                best = (np.median(d), sg)
        P = np.c_[P3[:, 0], best[1] * P3[:, 2]]
        s, x, z, nx, nz, _ = _frame(P)
        u = _cast(segs, x, z, nx, nz)
        eL, eR = _fill(u[0]), _fill(u[1])
        found = [float(np.isfinite(u[0]).mean()), float(np.isfinite(u[1]).mean())]
        src = {"workshop": str(workshop), "obj_frame_z_sign": best[1]}
    else:
        LJ = json.loads(line.read_text(encoding="utf-8"))
        P3 = np.array(LJ["points_xyz_m"])
        P = np.c_[P3[:, 0], P3[:, 2]]
        s, x, z, nx, nz, seg = _frame(P)
        w = np.interp(s, seg, np.array(LJ["widths_m"], dtype=float))
        eL, eR = w / 2, w / 2
        found = [1.0, 1.0]
        src = {"line": str(line)}
    meas, covered = measured_series(track, cfg, s, x, z, nx, nz)
    rep = {"track": track.name, **src, "lap_m": round(float(s[-1]), 1), "edges_found": [round(f, 4) for f in found],
           "params": {k: getattr(ED, k) for k in ("SAMPLE_M", "MAX_LEN_M", "MIN_LEN_M", "MIN_AMP_M", "EPS_M", "OUT_M",
                                                  "REAL_SHARE", "REAL_T", "MIN_MEASURED")},
           "lidar_edges_cover": covered, "skip": skip, "series": {}}
    series = {"left": eL, "right": eR, "width": eL + eR}
    keep = {}
    km = float(s[-1]) / 1000
    for name, e in series.items():
        sr, yr, rows = analyse(s, e, meas[name], closed, skip, 3 if name == "width" else ED.MIN_MEASURED)
        keep[name] = (sr, yr, rows)
        counted = [r for r in rows if not r["skipped"] and r["kind"] == "bulge"]
        rep["series"][name] = {
            "bulges": [{k: v for k, v in r.items() if k != "_i"} for r in rows],
            "per_km": {v: round(sum(1 for r in counted if r["verdict"] == v) / km, 2) for v in ("ours", "real", "unmeasured")},
            "count": {v: sum(1 for r in counted if r["verdict"] == v) for v in ("ours", "real", "unmeasured")},
            "ours_amp_m_max": round(max([r["amp_m"] for r in counted if r["verdict"] == "ours"] or [0.0]), 3),
            "ours_len_m_total": round(sum(r["len_m"] for r in counted if r["verdict"] == "ours"), 1)}
    # the second signal: the edge's plan curvature against a parallel offset of the line's
    kl = _curv(x, z)
    wob = {}
    for name, sg, e in (("left", 1.0, eL), ("right", -1.0, eR)):
        ex, ez = x + sg * e * nx, z + sg * e * nz
        ke = _curv(ex, ez)
        expect = kl / np.maximum(1 - sg * e * kl, 0.2)
        dk = _band(ke - expect, 2, 30)
        turn = np.abs(kl) >= FLIP_KAPPA
        flips = turn & (np.sign(ke) != np.sign(kl)) & (np.abs(ke) > FLIP_KAPPA)
        per = [float(np.sqrt(np.mean(dk[(s >= q) & (s < q + 100)] ** 2)) * 1000) for q in range(0, int(s[-1]) - 50, 100)]
        wob[name] = {"wobble_2_30m_1pkm_p50_p90_max": [round(float(np.percentile(per, q)), 3) for q in (50, 90, 100)],
                     "flip_m_per_km": round(float(flips.sum() * DS / km), 2)}
    rep["curvature"] = wob
    return rep, keep, meas


def png(prefix: str, rep, keep, meas, row_m=400.0, exag=10.0):
    from PIL import Image, ImageDraw
    sr = np.array(keep["left"][0])
    lap = sr[-1]
    rows = int(math.ceil(lap / row_m))
    W, RH = 2000, 300
    img = Image.new("RGB", (W + 100, rows * RH + 40), (250, 250, 247))
    d = ImageDraw.Draw(img)
    pxs = W / row_m
    col = {"ours": (220, 60, 60), "real": (60, 170, 80), "unmeasured": (150, 150, 150)}
    d.text((10, 8), f"{rep['track']}: lane edges along the lap, {row_m:.0f} m a row, the offset x{exag:.0f} about its own lap "
                    f"median. Black = built edge; blue = measured 5 m medians; shaded = a bulge (red ours / green real / grey "
                    f"unmeasured)", fill=(0, 0, 0))
    for side, y0f in (("left", 0.30), ("right", 0.70)):
        e = np.array(keep[side][1])
        med = float(np.median(e))
        mm = meas[side]
        for r in range(rows):
            a, b = r * row_m, (r + 1) * row_m
            oy = 40 + r * RH + y0f * RH
            pyu = pxs * exag
            m = (sr >= a) & (sr < b)
            for bl in keep[side][2]:
                if bl["s"][1] >= a and bl["s"][0] < b:
                    x0, x1 = 60 + (max(bl["s"][0], a) - a) * pxs, 60 + (min(bl["s"][1], b) - a) * pxs
                    d.rectangle([x0, oy - 60, x1, oy + 60], fill=tuple(int(c * 0.3 + 250 * 0.7) for c in col[bl["verdict"]]))
            ms = [(t, v) for t, v in mm if a <= t < b]
            for q in np.arange(a, b, 5.0):
                v = [vv for t, vv in ms if q <= t < q + 5]
                if len(v) >= 3:
                    yy = oy - (ED._median(v) - med) * pyu
                    xx = 60 + (q + 2.5 - a) * pxs
                    d.ellipse([xx - 3, yy - 3, xx + 3, yy + 3], fill=(40, 100, 210))
            pts = [(60 + (t - a) * pxs, oy - (v - med) * pyu) for t, v in zip(sr[m], e[m])]
            if len(pts) > 1:
                d.line(pts, fill=(0, 0, 0), width=2)
            d.text((4, oy - 8), f"{side[0].upper()} s{int(a)}", fill=(90, 90, 90))
        for r in range(rows):
            d.line([(60, 40 + r * RH), (W + 60, 40 + r * RH)], fill=(200, 200, 200))
    img.save(prefix + ".png")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("track")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--workshop")
    g.add_argument("--line")
    ap.add_argument("--out")
    ap.add_argument("--png")
    a = ap.parse_args(argv)
    rep, keep, meas = run(Path(a.track), Path(a.workshop) if a.workshop else None, Path(a.line) if a.line else None)
    if a.out:
        Path(a.out).write_text(json.dumps(rep, indent=1), encoding="utf-8")
    if a.png:
        png(a.png, rep, keep, meas)
    for name, v in rep["series"].items():
        print(f"[edge_bulges] {rep['track']} {name}: bulges ours {v['count']['ours']} ({v['per_km']['ours']}/km, max "
              f"{v['ours_amp_m_max']} m, {v['ours_len_m_total']} m long), real {v['count']['real']}, unmeasured "
              f"{v['count']['unmeasured']}")
    for name, v in rep["curvature"].items():
        print(f"[edge_bulges] {rep['track']} {name} edge curvature wobble 2-30 m (1/km per 100 m) p50/p90/max "
              f"{v['wobble_2_30m_1pkm_p50_p90_max']}, flips {v['flip_m_per_km']} m/km")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""The road's height and banking from the measured surface (fleet round 1; Kevin 2026-11-13: "Milford still seems
wavy as driven"; opt-in lm_intake.measured_surface).

What was wrong (measured on Milford 0.1.11's built road against the G10's raw-lidar read of the same lanes, board asset
d74be8dc7f28b114c66f909ae18e2fcb): the built centre is the 3DEP profile (a 33 m median + 9 m mean) and its banking is
the 2017 camber survey (source/lidar/camber-survey/crossfall.json: read every 3 m over +-5 m, every read over 12 %
DROPPED [MAX_READ_PCT, invented], capped at 12 %, smoothed 9 m). On the +-4.5 m lanes the built road's 30-120 m waves
are not the lidar's (gain 0.40-0.73 at 30-60 m; diffs 2.5-4.6 cm RMS), the banking's 30-300 m changes are not the
lidar's at all (gain 0.06-0.58; 0.5-1.1 % RMS off), and two infield corners the lidar reads at 17-18 % across seven
independent planes (s 862-923, 991-1233) were built flat (the survey's dropped reads).

The fix, in two halves:
  fit    (numpy; run once, its product committed): the G10's file holds, every 0.5 m of the port's line and at seven
         offsets -4.5..+4.5 m, a robust plane through the raw class-2 returns within 1.25 m (its height, its noise and
         a noise_beats_signal flag). Per station a weighted plane y = c + b o across the offsets (weights 1 / noise^2;
         one pass drops a point more than 4 noise + 2 cm off its station's plane), then along the lap a low-pass that
         is FLAT for long waves (a raised cosine in log wavelength: a Gaussian dulls the hills, 0.97 gain on 69 cm of
         120-300 m relief is 2 cm): pass >= PASS_M, stop <= STOP_M; where the lidar's own noise shakes the car as much
         as its bumps (the share of the seven paths flagged, smoothed 10 m) the cutoff doubles (PASS_HI_M / STOP_HI_M).
         Written: c (the built frame's height at the line, the deck's +0.10 included, as the G10's y_m), b (tan of the
         bank, + = left of travel higher), every RESAMPLE_EVERY-th station.
  apply  (stdlib; tools/lm_engine_intake.py): each point of the line the assembler will build (its smoothed X / Z) is
         put on the product's stations by position (the nearest station, interpolated along, the lateral offset u off
         the measured line taken on the plane: c + u b, so a line moved sideways keeps the measured surface), and the
         intake sets the line's Y = c - the deck, the bank = atan(b) (data/crossfall.lm.json, the assembler's
         route.crossfall_file). The assembler's own Y smoothing must be off (route.smooth_sigma_y_pts 0): the product
         IS the filtered surface.

    python tools/measured_surface.py fit <g10 surface.json> <out product.json> [--built <built paths .npy>]
    python tools/measured_surface.py section <g10 wide read of a stretch.json> <the fit product.json> <out section.json>
"""
from __future__ import annotations

import bisect
import json
import math
import sys
from pathlib import Path

PASS_M = 30.0          # [invented, measured basis] the lidar's 2-30 m content is its noise: 0.61 / 0.77 / 1.20 cm RMS
STOP_M = 15.0          #   at 2-6 / 6-15 / 15-30 m on the -4.5 m lane against a per-point noise of ~1 cm (the G10's
#                        split-half calibration); the drive's waves live at 30-300 m (0.5-4 Hz at 230 km/h is 16-128 m)
PASS_HI_M = 60.0       # [invented] where noise_beats_signal (the G10's 60 m body-band test) the cutoff doubles
STOP_HI_M = 30.0
FLAG_SMOOTH_M = 10.0   # [invented] the flag share smoothed so the cutoff never switches in one station
OUTLIER_K = 4.0        # [invented] a point off its station's plane by > OUTLIER_K noise + OUTLIER_M is dropped
OUTLIER_M = 0.02
NOISE_FLOOR_M = 0.005  # [invented] no point weighs more than a 5 mm noise
RESAMPLE_EVERY = 3     # 0.5 m -> 1.5 m stations (the filtered series has nothing under 15 m: 1.5 m is 10 a wave)
MAX_LATERAL_M = 4.5    # apply: a line point further than this off the measured line is outside the measured band
MAX_ALONG_M = 2.0      # apply: a line point further than this along from its nearest station is off the product


# ---------------------------------------------------------------------------------------------------------- fit
def fit(g10: dict, built=None) -> dict:
    import numpy as np
    keys = ["-4.5", "-3.0", "-1.5", "+0.0", "+1.5", "+3.0", "+4.5"]
    offs = [float(k) for k in keys]
    if [float(o) for o in g10["frame"]["offsets_m"]] != offs:
        raise SystemExit(f"[measured_surface] offsets {g10['frame']['offsets_m']}: expected {offs}")
    n = int(g10["stations"])
    step = float(g10["step_m"])
    O = np.array(offs)[:, None]
    Y = np.array([[np.nan if v is None else v for v in g10["paths"][k]["y_m"]] for k in keys], dtype=float)
    N = np.array([[np.nan if v is None else v for v in g10["paths"][k]["noise_m"]] for k in keys], dtype=float)
    FL = np.array([g10["paths"][k]["noise_beats_signal"] for k in keys], dtype=float)
    W = np.where(np.isfinite(N) & np.isfinite(Y), 1.0 / np.maximum(N, NOISE_FLOOR_M) ** 2, 0.0)

    def plane(Yv, Wv):
        Wv = np.where(np.isfinite(Yv), Wv, 0.0)
        Yz = np.where(np.isfinite(Yv), Yv, 0.0)
        s0 = Wv.sum(0); s1 = (Wv * O).sum(0); s2 = (Wv * O * O).sum(0)
        t0 = (Wv * Yz).sum(0); t1 = (Wv * O * Yz).sum(0)
        det = s0 * s2 - s1 * s1
        ok = (det > 1e-9) & ((Wv > 0).sum(0) >= 3)
        dd = np.where(ok, det, 1.0)
        return (np.where(ok, (s2 * t0 - s1 * t1) / dd, np.nan), np.where(ok, (s0 * t1 - s1 * t0) / dd, np.nan), ok)

    c, b, ok = plane(Y, W)
    res = Y - (c[None] + O * b[None])
    bad = np.abs(res) > OUTLIER_K * np.nan_to_num(N, nan=OUTLIER_M) + OUTLIER_M
    Y2 = np.where(bad, np.nan, Y)
    c, b, ok = plane(Y2, W)
    res2 = Y2 - (c[None] + O * b[None])

    k = np.fft.rfftfreq(n, d=step)
    lam = np.where(k > 0, 1.0 / np.maximum(k, 1e-12), np.inf)

    def lowpass(v, pass_m, stop_m):
        idx = np.arange(n)
        good = np.isfinite(v) & ok
        vf = np.interp(idx, np.flatnonzero(good), v[good], period=n)
        t = np.clip((np.log(lam) - math.log(stop_m)) / (math.log(pass_m) - math.log(stop_m)), 0.0, 1.0)
        return np.fft.irfft(np.fft.rfft(vf) * (0.5 - 0.5 * np.cos(np.pi * t)), n)

    share = FL.mean(0)
    Hg = np.exp(-2.0 * (np.pi * k * FLAG_SMOOTH_M) ** 2)
    wfl = np.clip(np.fft.irfft(np.fft.rfft(share) * Hg, n), 0.0, 1.0)
    cf = (1 - wfl) * lowpass(c, PASS_M, STOP_M) + wfl * lowpass(c, PASS_HI_M, STOP_HI_M)
    bf = (1 - wfl) * lowpass(b, PASS_M, STOP_M) + wfl * lowpass(b, PASS_HI_M, STOP_HI_M)

    # the longest run of stations with no plane (filled by the interpolation + the filter)
    run = best = 0
    for v in ok.tolist() + ok.tolist():
        run = 0 if v else run + 1
        best = max(best, run)
    best = min(best, n)
    rep = {"stations": n, "step_m": step, "plane_points": int(np.isfinite(Y).sum()),
           "plane_points_dropped": int(np.nansum(bad & np.isfinite(Y))),
           "plane_resid_m": {q: round(float(np.nanpercentile(np.abs(res2), p)), 4) for q, p in (("p50", 50), ("p90", 90), ("p99", 99))},
           "stations_without_plane": int((~ok).sum()), "longest_gap_m": round(best * step, 1),
           "flag_share_mean": round(float(share.mean()), 3),
           "bank_pct": {"p50_abs": round(float(np.percentile(np.abs(100 * bf), 50)), 2),
                        "p95_abs": round(float(np.percentile(np.abs(100 * bf), 95)), 2),
                        "max_abs": round(float(np.max(np.abs(100 * bf))), 2)}}
    # the worst bank change in any 30 m (reported; no gate in this chain reads it)
    w30 = int(round(30.0 / step))
    bb = np.concatenate([bf, bf[:w30]])
    ch = max(float(np.max(bb[i:i + w30 + 1]) - np.min(bb[i:i + w30 + 1])) for i in range(0, n, 4))
    rep["bank_worst_change_pct_per_30m"] = round(100 * ch, 2)
    if built is not None:
        rep["against_built"] = _bands(np, Y2, np.asarray(built), cf, bf, O, step, keys)
    sel = list(range(0, n, RESAMPLE_EVERY))
    return {"_doc": "tools/measured_surface.py fit (fleet round 1): the road surface from the G10's raw-lidar read, a "
                    "plane per station, low-passed flat above PASS_M; c = the built frame's height at the line (the deck's "
                    "+0.10 inside it, the G10's y_m datum), b = tan(bank), + = left of travel higher",
            "frame": "ENU local metres (X = east, Z = north), the port line's origin; s along data/centerline.local.json",
            "line_md5": (g10.get("inputs") or {}).get("line_md5"),
            "lap_m": float(g10["lap_m"]),
            "params": {"PASS_M": PASS_M, "STOP_M": STOP_M, "PASS_HI_M": PASS_HI_M, "STOP_HI_M": STOP_HI_M,
                       "FLAG_SMOOTH_M": FLAG_SMOOTH_M, "OUTLIER_K": OUTLIER_K, "OUTLIER_M": OUTLIER_M,
                       "NOISE_FLOOR_M": NOISE_FLOOR_M, "RESAMPLE_EVERY": RESAMPLE_EVERY},
            "datum": g10.get("datum"), "registration_lidar_shift_m": g10.get("registration_lidar_shift_m"),
            "report": rep,
            "s": [round(float(g10["s"][i]), 2) for i in sel], "x": [round(float(g10["x"][i]), 3) for i in sel],
            "z": [round(float(g10["z"][i]), 3) for i in sel], "nx": [round(float(g10["nx"][i]), 5) for i in sel],
            "nz": [round(float(g10["nz"][i]), 5) for i in sel], "c": [round(float(cf[i]), 4) for i in sel],
            "b": [round(float(bf[i]), 5) for i in sel], "noise_weight": [round(float(wfl[i]), 3) for i in sel]}


def _bands(np, Yl, Yb, cf, bf, O, step, keys):
    """the built road (Yb, the same seven paths) and the new surface against the lidar, per wave band (cm RMS)"""
    n = Yl.shape[1]
    Yn = cf[None] + O * bf[None]
    k = np.fft.rfftfreq(n, d=step)
    lam = np.where(k > 0, 1.0 / np.maximum(k, 1e-12), np.inf)

    def band(v, lo, hi):
        good = np.isfinite(v)
        v = np.interp(np.arange(n), np.flatnonzero(good), v[good], period=n)
        F = np.fft.rfft(v - v.mean())
        F[(lam < lo) | (lam >= hi)] = 0
        return np.fft.irfft(F, n)
    out = {}
    for j, key in enumerate(keys):
        row = {}
        for lo, hi in ((15, 30), (30, 60), (60, 120), (120, 300)):
            L, B, Nn = band(Yl[j], lo, hi), band(Yb[j], lo, hi), band(Yn[j], lo, hi)
            r = lambda v: round(float(100 * np.sqrt(np.mean(v ** 2))), 2)
            row[f"{lo}-{hi} m"] = {"lidar_cm": r(L), "built_cm": r(B), "new_cm": r(Nn), "built_minus_lidar_cm": r(B - L),
                                   "new_minus_lidar_cm": r(Nn - L),
                                   "gain_built": round(float(np.dot(B, L) / np.dot(L, L)), 2),
                                   "gain_new": round(float(np.dot(Nn, L) / np.dot(L, L)), 2)}
        out[key] = row
    moved = np.abs(Yn - Yb)
    out["moved_m"] = {q: round(float(np.nanpercentile(moved, p)), 3) for q, p in (("p50", 50), ("p90", 90), ("p99", 99), ("max", 100))}
    return out


# -------------------------------------------------------------------------------------------------------- apply
class Product:
    """the committed product, for the intake (stdlib only)"""

    def __init__(self, d: dict):
        self.s, self.x, self.z = d["s"], d["x"], d["z"]
        self.nx, self.nz, self.c, self.b = d["nx"], d["nz"], d["c"], d["b"]
        self.n = len(self.s)
        self.lap = float(d["lap_m"])
        self.cell = 6.0
        self.grid: dict = {}
        for i in range(self.n):
            self.grid.setdefault((int(self.x[i] // self.cell), int(self.z[i] // self.cell)), []).append(i)

    def _nearest(self, x, z):
        bx, bz = int(x // self.cell), int(z // self.cell)
        best, bi = None, None
        for r in range(0, 4):
            for dx in range(-r, r + 1):
                for dz in range(-r, r + 1):
                    if max(abs(dx), abs(dz)) != r:
                        continue
                    for i in self.grid.get((bx + dx, bz + dz), ()):
                        d = (self.x[i] - x) ** 2 + (self.z[i] - z) ** 2
                        if best is None or d < best:
                            best, bi = d, i
            # ledger 0102: stop only when no station in ring r + 1 or further can be nearer (every one there is at least
            # r cells away, the point sitting anywhere in its own cell). Stopping after ring 1 whenever ring 0/1 held any
            # station gave a point more than a cell off the line a farther station: on the inside of Milford's GM turn
            # section() put u >= +7.0 at s 970-976 on station s 966.0, and its delta jumped +0.27..+0.47 m across 0.5 m.
            # The intake's points are within ~1 m of the product's line and stop at ring 1 exactly as before.
            if bi is not None and best <= (r * self.cell) ** 2:
                break
        return bi

    def at(self, x, z):
        """(height c + u b at the point, tan bank, lateral u, along v) or None off the product"""
        i = self._nearest(x, z)
        if i is None:
            return None
        tx, tz = self.nz[i], -self.nx[i]            # the tangent: the normal (+ = left) turned -90 deg
        ex, ez = x - self.x[i], z - self.z[i]
        v = ex * tx + ez * tz
        u = ex * self.nx[i] + ez * self.nz[i]
        j = (i + (1 if v >= 0 else -1)) % self.n
        ds = abs(self.s[j] - self.s[i])
        if ds > self.lap / 2:
            ds = self.lap - ds
        t = min(1.0, abs(v) / ds) if ds > 1e-9 else 0.0
        c = self.c[i] + (self.c[j] - self.c[i]) * t
        b = self.b[i] + (self.b[j] - self.b[i]) * t
        return c + u * b, b, u, abs(v) - t * ds


def apply(product: dict, pts_xz, deck_m: float):
    """line Y (= the measured height at each smoothed point - the deck) and bank_rad, per point; a report.
    SystemExit when a point lies off the measured band (the product was measured on another line)."""
    P = Product(product)
    ys, banks, us = [], [], []
    for k, (x, z) in enumerate(pts_xz):
        r = P.at(x, z)
        if r is None:
            raise SystemExit(f"[measured_surface] line point {k} ({x:.1f}, {z:.1f}) has no measured station near it")
        h, b, u, v_off = r
        if abs(u) > MAX_LATERAL_M or v_off > MAX_ALONG_M:
            raise SystemExit(f"[measured_surface] line point {k} ({x:.1f}, {z:.1f}) is {u:+.2f} m across / {v_off:.2f} m "
                             f"along off the measured line (max {MAX_LATERAL_M} / {MAX_ALONG_M}): measured on another line")
        ys.append(h - deck_m)
        banks.append(math.atan(b))
        us.append(u)
    au = sorted(abs(u) for u in us)
    return ys, banks, {"points": len(ys), "lateral_off_measured_line_m": {"p50": round(au[len(au) // 2], 3),
                                                                           "max": round(au[-1], 3)},
                       "bank_max_pct": round(100 * max(abs(math.tan(b)) for b in banks), 2)}


def section(g10w: dict, product: dict) -> dict:
    """ledger 0102 (Milford round 2, a real banked turn whose cross-section is not a plane): a WIDE read of one stretch (the
    G10's same read, more paths across, the same line) against the committed fit product. Per path the height is low-passed
    along the stretch by fit()'s own raised cosine (PASS_M / STOP_M; the stretch is not a lap, so the series is mirrored at
    both ends first), then delta = that height - the product's plane (c + u b) at the same point: what the plane misses, per
    station and offset, for tools/densify_ribbon_blend.py's opt-in route.densify.section."""
    import numpy as np
    keys = list(g10w["paths"].keys())
    offs = [float(k) for k in keys]
    if offs != sorted(offs):
        raise SystemExit(f"[measured_surface] section: offsets {offs} not in order")
    if (g10w.get("inputs") or {}).get("line_md5") != product.get("line_md5"):
        raise SystemExit(f"[measured_surface] section: the read's line {(g10w.get('inputs') or {}).get('line_md5')} is not "
                         f"the product's {product.get('line_md5')}")
    n = len(g10w["s"])
    step = float(g10w["step_m"])
    Y = np.array([[np.nan if v is None else v for v in g10w["paths"][k]["y_m"]] for k in keys], dtype=float)
    k_ = np.fft.rfftfreq(3 * n, d=step)
    lam = np.where(k_ > 0, 1.0 / np.maximum(k_, 1e-12), np.inf)
    H = 0.5 - 0.5 * np.cos(np.pi * np.clip((np.log(lam) - math.log(STOP_M)) / (math.log(PASS_M) - math.log(STOP_M)),
                                           0.0, 1.0))
    P = Product(product)
    X, Z, NX, NZ, S = (np.asarray(g10w[q], dtype=float) for q in ("x", "z", "nx", "nz", "s"))
    D = np.full(Y.shape, np.nan)
    filled = []
    for j, u in enumerate(offs):
        v = Y[j]
        good = np.isfinite(v)
        filled.append(int((~good).sum()))
        if good.sum() < 10:
            continue
        vf = np.interp(np.arange(n), np.flatnonzero(good), v[good])
        ext = np.concatenate([vf[::-1], vf, vf[::-1]])
        lp = np.fft.irfft(np.fft.rfft(ext) * H, 3 * n)[n:2 * n]
        for i in range(n):
            r = P.at(X[i] + u * NX[i], Z[i] + u * NZ[i])
            if r is not None:
                D[j, i] = lp[i] - r[0]
    sel = list(range(0, n, RESAMPLE_EVERY))
    a = np.abs(D[:, sel])
    rep = {"stations": n, "step_m": step, "s_m": [round(float(S[0]), 1), round(float(S[-1]), 1)], "offsets_m": offs,
           "missing_samples_per_path": dict(zip(keys, filled)),
           "delta_abs_m": {"p50": round(float(np.nanpercentile(a, 50)), 3), "p95": round(float(np.nanpercentile(a, 95)), 3),
                           "max": round(float(np.nanmax(a)), 3)}}
    return {"_doc": "tools/measured_surface.py section (ledger 0102): what the fit product's plane misses across one stretch, "
                    "per station and offset: delta = the wide read's height (low-passed along, PASS_M / STOP_M) - (c + u b)",
            "frame": product.get("frame"), "line_md5": product.get("line_md5"), "lap_m": product.get("lap_m"),
            "offsets_m": offs, "report": rep,
            "s": [round(float(S[i]), 2) for i in sel], "x": [round(float(X[i]), 3) for i in sel],
            "z": [round(float(Z[i]), 3) for i in sel], "nx": [round(float(NX[i]), 5) for i in sel],
            "nz": [round(float(NZ[i]), 5) for i in sel],
            "delta": [[None if not np.isfinite(D[j, i]) else round(float(D[j, i]), 4) for j in range(len(offs))] for i in sel]}


def main(argv):
    if len(argv) >= 4 and argv[0] == "section":
        import hashlib
        g10w = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        prod = json.loads(Path(argv[2]).read_text(encoding="utf-8"))
        out = section(g10w, prod)
        out["input"] = {"file": Path(argv[1]).name, "md5": hashlib.md5(Path(argv[1]).read_bytes()).hexdigest(),
                        "product": Path(argv[2]).name, "product_md5": hashlib.md5(Path(argv[2]).read_bytes()).hexdigest()}
        Path(argv[3]).write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
        print(json.dumps(out["report"], indent=1))
        return 0
    if len(argv) >= 3 and argv[0] == "fit":
        g10 = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        built = None
        if "--built" in argv:
            import numpy as np
            built = np.load(argv[argv.index("--built") + 1])
        out = fit(g10, built)
        import hashlib
        out["input"] = {"file": Path(argv[1]).name, "md5": hashlib.md5(Path(argv[1]).read_bytes()).hexdigest()}
        Path(argv[2]).write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
        print(json.dumps(out["report"], indent=1))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

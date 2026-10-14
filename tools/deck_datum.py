"""Hold a real bridge deck between its REAL abutments, at the road's REAL height (fleet/LAWS.md L3, "Bridges dip";
ledger 0046 v0.18.0 integration fix round, the truth lens's criterion 4 at College Ave north of I-8).

WHY. The loop's raw centreline carries a level deck over each I-8 crossing, interpolated between two approach heights
long before 0046. At College Ave that deck was laid from s 2568 to s 2697 (pre-median stations), 25 m past the real
north abutment, starting from an approach height that was the slope under the bridge, not the road. Fresh 3DEP 1 m
along the centreline (2026-10-13) shows the real road: an embankment at road height up to s ~2586 (108.65 m), the
open span to s ~2683, then the road on its north embankment at 112.4-113.4 m. The built road there was 2.0-3.0 m
LOW for 60 m (s 2679-2739), then climbed at ~10 % to catch up — a sag and a grade break the real road does not have,
and the ground pinned under it was 2.5 m under the real verge (criterion 4, section 2050 north rim).

WHAT. For every deck declared in track.config.json road_datum.decks (stations on the PRE-MEDIAN centreline, the file
this edits) the tool reads 3DEP every 1 m along that centreline over the deck's window (cached in
data/deck_datum.samples.json with provenance; missing points fetched, TLS verified), and sets the road height:
  * on the approaches (window start .. abutment A, abutment B .. window end): the 3DEP road surface, a one-sided
    +-SMOOTH_M moving average that never reads across an abutment into the bare earth under the span;
  * on the deck (A .. B): a straight line between those two abutment heights (a deck is a straight girder line);
  * blended into the existing profile over BLEND_M at both window ends (no step).
Only y changes; plan positions are untouched. median_envelope then re-centres the line as before, and the assembler's
own light smoothing (smooth_sigma_y_pts) runs on top.

PROFILE WINDOWS (ledger 0057, Kevin 2026-10-14: "my cars with clutches would roll back from stoplights there"). The
frozen pre-median profile carries the August heightfield smoothing (33 m median + two 39 m box means + the lap-seam
blend, scripts-v021/elevation/heightfield.py), which rounds every short feature: the College -> Alvarado signal
approach was built at +3.5 % against a real +5.9 %, Alvarado's pitch down from 70th at -6.1 % against -7.7 %. For every
window declared in track.config.json road_datum.profiles (pre-median stations; a window whose start is past its end
runs through the lap seam, L13 — the closing duplicate vertex is never a second vertex, it takes v0's height) the tool
reads 3DEP every 1 m at BOTH carriageway centres (a quarter of the road width either side of the line: the mean of the
two is the slab's height, so a crowned centre line or one tilted half never sets it), holds every declared deck span
that lies inside the window straight between its abutments (the same one-sided SMOOTH_M reads, so a profile never
dips into a creek or a freeway trench), smooths that lightly (a Gaussian of PROFILE_SIGMA_M) and blends it into the
existing profile over the window's blend_m at both ends. A window's fold_fan_fit (a levelled fold fan inside it,
ledger 0050) then takes the smallest change that keeps the fan's own gate on the ribbon the build will carry (see
"the fold-fan fit" below; it replaced round 1's hold_straight_m box, which held the junction's crest 0.55 m low). Decks
run first, profiles second: a deck inside a profile is held straight by the profile (its own window pass is skipped
and reported re_derived_by_profile), a deck outside every profile is exactly as before. The road stays a level slab
across its width: the real junction tilts 4-8 % across, and the race walls' containment band (no_route,
verify_fold_fans (7): +-0.28 m about the centre line) cannot carry that 14 m from the line (ledger 0057).
The assembler (scripts-v021/blender/build_loop_blend.py) reads the same windows and smooths them with their own
assembler_sigma_y_pts instead of route.smooth_sigma_y_pts, so its Gaussian does not round the real grade back off.

Idempotent: data/deck_datum.json records the md5 of the file it wrote; a run that finds that md5 on its input
(already corrected, e.g. run twice without the ship chain's re-sync) changes nothing.

    python tools/deck_datum.py <project-dir> [--offline]
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]
if str(AIROSO) not in sys.path:
    sys.path.insert(0, str(AIROSO))

SAMPLE_M = 1.0      # 3DEP spacing along the centreline
SMOOTH_M = 3.0      # [invented] one-sided moving-average half window on the approaches
BLEND_M = 8.0       # [invented] blend into the existing profile at each window end
PROFILE_SIGMA_M = 3.0    # [invented] profile windows: Gaussian sigma on the 1 m 3DEP profile (= 1 centreline vertex,
#                          ~3 m: rounds the 1 m DEM's +-10 cm sample noise; swept 2-6 m on the two windows, ledger
#                          0057 — 6 m cost the College / 70th stop-line approaches another 0.07 / 0.21 points and
#                          bought nothing the gates need; GATES-CHANGELOG 2026-10-14)
PROFILE_BLEND_M = 30.0   # [invented] profile windows: default blend at each end (road_datum.profiles[].blend_m)
SRC_NAME = "centerline.raw.local.json.pre-median"


def stations(pts):
    s = [0.0]
    for a, b in zip(pts, pts[1:]):
        s.append(s[-1] + math.hypot(b[0] - a[0], b[2] - a[2]))
    return s


def point_at(pts, st, t):
    """(x, z) on the polyline at station t"""
    k = 0
    while k < len(st) - 2 and st[k + 1] < t:
        k += 1
    L = st[k + 1] - st[k] or 1e-9
    u = (t - st[k]) / L
    a, b = pts[k], pts[k + 1]
    return a[0] + (b[0] - a[0]) * u, a[2] + (b[2] - a[2]) * u


def target_profile(ts, dep, deck_m):
    """road height at each 1 m sample ``ts`` from 3DEP ``dep``: one-sided moving average on the approaches (never
    across an abutment), a straight deck between the two abutment heights"""
    a, b = deck_m
    out = []

    def avg(lo, hi):
        vals = [d for t, d in zip(ts, dep) if lo - 1e-6 <= t <= hi + 1e-6]
        return sum(vals) / len(vals)
    ya = avg(a - SMOOTH_M, a)
    yb = avg(b, b + SMOOTH_M)
    for t in ts:
        if t <= a:
            out.append(avg(t - SMOOTH_M, min(t + SMOOTH_M, a)))
        elif t >= b:
            out.append(avg(max(t - SMOOTH_M, b), t + SMOOTH_M))
        else:
            out.append(ya + (yb - ya) * (t - a) / (b - a))
    return out, ya, yb


def interp(ts, ys, t):
    if t <= ts[0]:
        return ys[0]
    if t >= ts[-1]:
        return ys[-1]
    k = int((t - ts[0]) // SAMPLE_M)
    k = max(0, min(len(ts) - 2, k))
    u = (t - ts[k]) / (ts[k + 1] - ts[k])
    return ys[k] + (ys[k + 1] - ys[k]) * u


def apply_deck(st, ys_old, ts, target, window_m, blend=BLEND_M):
    """new heights for the polyline vertices at stations ``st`` (local y): inside the window the target, blended over
    ``blend`` m at both window ends; outside the window unchanged"""
    w0, w1 = window_m
    out = list(ys_old)
    for i, s in enumerate(st):
        if s < w0 or s > w1:
            continue
        w = min(1.0, (s - w0) / blend, (w1 - s) / blend)
        w = w * w * (3 - 2 * w)
        out[i] = ys_old[i] + w * (interp(ts, target, s) - ys_old[i])
    return out


# --- profile windows (ledger 0057) -------------------------------------------------------------------------------
def unwrap_window(window_m, L):
    """(w0, w1) on the window's own unwrapped station axis: a window whose start is past its end runs through the lap
    seam, so its end is taken one lap on (L13)"""
    w0, w1 = float(window_m[0]), float(window_m[1])
    if w1 < w0:
        w1 += L
    return w0, w1


def unwrapped(s, w0, w1, L):
    """station ``s`` (0 <= s <= L) on the window's unwrapped axis, or None when it lies outside the window"""
    for u in (s, s + L):
        if w0 - 1e-9 <= u <= w1 + 1e-9:
            return u
    return None


def ring_frame(pts, st, widths, t):
    """(x, z, tx, tz, width) at station ``t`` (taken modulo the lap on a closed line); the tangent spans +-3 vertices,
    across the seam on a closed line"""
    closed = abs(pts[0][0] - pts[-1][0]) < 1e-6 and abs(pts[0][2] - pts[-1][2]) < 1e-6
    L = st[-1]
    if closed:
        t = t % L
    t = max(0.0, min(L, t))
    lo, hi = 0, len(st) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if st[mid] <= t:
            lo = mid
        else:
            hi = mid
    k = lo
    u = (t - st[k]) / ((st[k + 1] - st[k]) or 1e-9)
    a, b = pts[k], pts[k + 1]
    x, z = a[0] + (b[0] - a[0]) * u, a[2] + (b[2] - a[2]) * u
    m = len(pts) - 1
    if closed:
        p0, p1 = pts[(k - 3) % m], pts[(k + 4) % m]
    else:
        p0, p1 = pts[max(0, k - 3)], pts[min(len(pts) - 1, k + 4)]
    tx, tz = p1[0] - p0[0], p1[2] - p0[2]
    n = math.hypot(tx, tz) or 1e-9
    w = widths[k] + (widths[k + 1] - widths[k]) * u
    return x, z, tx / n, tz / n, w


def profile_samples(w0, w1):
    """the 1 m stations a profile window reads: the window plus the Gaussian's reach (and SMOOTH_M) either side"""
    margin = 3.0 * PROFILE_SIGMA_M + SMOOTH_M
    return [w0 - margin + k * SAMPLE_M for k in range(int(round((w1 - w0 + 2 * margin) / SAMPLE_M)) + 1)]


def carriageway_centres(pts, st, widths, ts):
    """[((x, z) left, (x, z) right)] at each station: both carriageway centres, a quarter of the road width either
    side of the line"""
    out = []
    for t in ts:
        x, z, tx, tz, w = ring_frame(pts, st, widths, t)
        off = w / 4.0
        out.append(((x - tz * off, z + tx * off), (x + tz * off, z - tx * off)))
    return out


def gauss_smooth(vals, sigma_samples):
    """a Gaussian (sigma in samples, cut at 3 sigma) that renormalises at the ends of the series"""
    if sigma_samples <= 0:
        return list(vals)
    r = max(1, int(round(3.0 * sigma_samples)))
    ker = [math.exp(-(k * k) / (2.0 * sigma_samples * sigma_samples)) for k in range(-r, r + 1)]
    n = len(vals)
    out = []
    for i in range(n):
        acc = wsum = 0.0
        for k in range(-r, r + 1):
            j = i + k
            if 0 <= j < n:
                acc += ker[k + r] * vals[j]
                wsum += ker[k + r]
        out.append(acc / wsum)
    return out


def profile_target(ts, raw, spans, sigma_m=PROFILE_SIGMA_M):
    """the road height at each 1 m sample ``ts`` of a profile window from the 3DEP road surface ``raw``: every deck
    span (a, b) inside it held straight between its abutments (one-sided SMOOTH_M reads, never across an abutment),
    then a Gaussian of ``sigma_m``. Returns (target, [(ya, yb) per span])"""
    vals = list(raw)
    held = []
    for a, b in spans:
        def avg(lo, hi):
            v = [d for t, d in zip(ts, raw) if lo - 1e-6 <= t <= hi + 1e-6]
            if not v:
                raise SystemExit(f"[deck] profile: no 3DEP sample in {lo:.1f}-{hi:.1f} m beside a span")
            return sum(v) / len(v)
        ya, yb = avg(a - SMOOTH_M, a), avg(b, b + SMOOTH_M)
        for i, t in enumerate(ts):
            if a < t < b:
                vals[i] = ya + (yb - ya) * (t - a) / (b - a)
        held.append((ya, yb))
    step = (ts[1] - ts[0]) if len(ts) > 1 else SAMPLE_M
    return gauss_smooth(vals, sigma_m / step), held


def apply_profile(us, ys_old, ts, target, w0, w1, blend):
    """new heights for vertices at unwrapped stations ``us`` (None = outside the window): the target inside, blended
    over ``blend`` m (smoothstep) at both ends; outside the window the old height, untouched"""
    out = list(ys_old)
    for i, u in enumerate(us):
        if u is None:
            continue
        w = min(1.0, (u - w0) / blend, (w1 - u) / blend)
        if w <= 0.0:
            continue
        w = w * w * (3 - 2 * w)
        out[i] = ys_old[i] + w * (interp(ts, target, u) - ys_old[i])
    return out


def window_spans(decks, w0, w1, L):
    """the declared deck spans lying inside the unwrapped window [w0, w1] (on its axis); a span cut by the window's
    edge is refused — the profile would read a trench at one abutment"""
    out = []
    for d in decks:
        a, b = (float(v) for v in d["deck_m"])
        for sh in (0.0, L):
            A, B = a + sh, b + sh
            if w0 <= A and B <= w1:
                out.append((A, B, d["name"]))
                break
            if A < w1 and B > w0:
                raise SystemExit(f"[deck] profile window {w0:.0f}-{w1:.0f} cuts deck {d['name']} {a:.0f}-{b:.0f}: a "
                                 f"deck span lies wholly inside or wholly outside a profile window")
    return out


# --- the fold-fan fit (ledger 0057 fix round) ----------------------------------------------------------------------
# A profile window may hold a LEVELLED fold fan (ledger 0050): a 24-30 m ribbon swung round a corner tighter than its
# half-width, its inside edge pinched to ONE point X at the midpoint of its legs (tools/mouth_weld.unfold_line). Every
# wheel path inside the corner folds too and is cut at its own self-intersection, so it turns sharply at a point on
# the corner's medial axis, and across that turn its grade jumps by the surface's slope along the axis (from X up to
# the centre rows) times up to ~1.9. The College/Alvarado junction's real crest (+5.3 % up from Alvarado, -5.2 % down
# College, 0.55 m over X) inside the hairpin's fan read DT 0.087 m on those paths (verify_fold_fans, 1st rehearsal);
# the first fix held a box straight through the fan, which passed but left the crest 0.55 m low and the stop line's
# last metres flat. drive_test's fixed-offset wheel paths judge the same corner too: inside a turn that tight each
# metre's sample jumps sideways where the segment normal turns, so the crest also read 10 street / 9-10 race severe
# steps and ~35 street kinks there (rehearsal 5, the fit on the fan alone). The fit replaces the box: inside fit_m the
# profile takes the smallest change (least squares on the heights and grades the assembler will build) that keeps
# every fan pinch near the window within dt_max_m on verify_fold_fans' own pinch paths AND leaves drive_test's wheel
# paths over the fit (street; both directions of a race lane) with no severe step and no more kinks than the frozen
# profile had there — all read on the ribbon the assembler and the weld will build (plan: the assembler's own
# smoothing of this line; heights: its per-window sigma_y; edges: mouth_weld.unfold_line, levelled). Outside fit_m
# nothing moves. Deterministic (coordinate descent from zero, fixed order). Refused when it cannot meet any of that,
# or when the full-resolution survey of the result exceeds the gate's own DT_MAX_M.
FAN_DT_MAX_M = 0.05        # [invented] verify_fold_fans DT_MAX_M 0.06 less 0.01: this model read 0.0868 / 0.0342 where
#                            the built gate read 0.087 / 0.034 (rehearsals 1 / 4); the solver's coarse survey reads at
#                            most 0.003 under the full one (measured on those two profiles)
FAN_BUMP_SPACING_M = 6.0   # [invented] ~2 centreline vertices between the fit's Gaussian bumps
FAN_BUMP_SIGMA_M = 4.5     # [invented] 1.5 vertex spacings: a bump moves a short stretch, never one vertex
FAN_TAPER_M = 12.0         # [invented] the bumps fade to zero over this at both ends of fit_m (smoothstep)
FAN_STEP0_M, FAN_STEP_MIN_M = 0.16, 0.01   # [invented] coordinate-descent step, halved down to 1 cm
FAN_PENALTY = 1.0e7        # per m^2 of DT over the solver's target: a hard wall (the objective is m^2 of height change)
FAN_SOLVE_DO_M, FAN_SOLVE_DS_M = 0.5, 0.1  # [invented] the solver's survey (the gate's: 0.25 / 0.05)
FAN_COARSE_MARGIN_M = 0.003  # [measured] the solver's survey read up to 0.0029 m under the full one (2026-10-14 fit):
#                              it solves to dt_max_m less this, and the full survey of the result must meet dt_max_m
FAN_MAX_EVALS = 2500       # a hard stop
FAN_MAX_MOVE_M = 0.25      # [invented] the fit may move a built height at most this far from the 3DEP target: a
#                            descent that settles in a far minimum (a pattern-search variant raised the junction's
#                            Alvarado leg 0.6 m, ledger 0057 fix round) is refused, never shipped
FAN_GRADE_WEIGHT_M2 = 100.0  # [invented] the fit's misfit weighs a 1 % grade error like a 0.1 m height error: on
#                              heights alone it bought a crest 0.05 m nearer the target with College's last 15 m to the
#                              stop line 1-1.5 points too steep (ledger 0057 fix round)
FAN_BEND_WEIGHT_M2 = 400.0  # [invented] ... and a 1 % change of grade between neighbouring vertices like a 0.2 m
#                             height error: without it the fit steepened College's flank and put a sag at its foot
#                             (s 2328-2346) where the seated ground's 10 m facets came up through the road by up to
#                             9 mm (drive_test soft tops 33 -> 39 street, 9 -> 21 race; rehearsal 6)
FAN_PAD_ROWS = 40          # rows surveyed past fit_m: a pinch's own rows +- the gate's window (B + PAD + 12 + 2)
FAN_WHEEL_PAD_ROWS = 10    # [invented] drive_test's wheel paths are walked over fit_m's rows +- this (~30 m)
FAN_COUNT_PENALTY = 1.0e3  # per severe step, and per kink over the frozen profile's (+ 0.1 per % point of kink excess
#                            over its, + 10 per m of step excess): a hard wall like FAN_PENALTY


def _load_smooth(cfg):
    """the assembler's own smoothing module (road_datum.assembler_smooth, a path under the airoso repo)"""
    rel = (cfg.get("road_datum") or {}).get("assembler_smooth")
    if not rel:
        raise SystemExit("[deck] fold_fan_fit needs road_datum.assembler_smooth (the assembler's smooth.py, relative "
                         "to the airoso repo) to predict the ribbon the build will carry")
    import importlib.util as u
    path = AIROSO / rel
    if not path.exists():
        raise SystemExit(f"[deck] road_datum.assembler_smooth: {path} not found")
    spec = u.spec_from_file_location("_assembler_smooth", path)
    mod = u.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fan_tools():
    tools = str(AIROSO / "tools")
    if tools not in sys.path:
        sys.path.insert(0, tools)
    import mouth_weld as mw
    import verify_fold_fans as vf
    return mw, vf


class _Assembler:
    """predicts the centreline the assembler builds from this pre-median line near a stretch: its plan smoothing
    (route.smooth_sigma_pts / smooth_passes) and its y smoothing (route.smooth_sigma_y_pts, each profile window's
    assembler_sigma_y_pts) — build_loop_blend's smooth_centerline call, exact where median_envelope leaves the stretch
    alone (it moves x/z beside a median, never at a fold fan; the built gates judge the result either way)"""

    def __init__(self, cfg, profiles, pts, st, closed):
        self.cfg = cfg
        self.sm = _load_smooth(cfg)
        route = cfg.get("route") or {}
        self.sig_y = float(route.get("smooth_sigma_y_pts", 1.5))
        self.ypasses = 2
        plan = self.sm.smooth_centerline([tuple(q) for q in pts], sigma_pts=float(route.get("smooth_sigma_pts", 2.0)),
                                         passes=int(route.get("smooth_passes", 2)), sigma_y_pts=0.0)
        self.plan = [(q[0], q[2]) for q in plan]
        lap = st[-1] if closed else None
        by = {}
        for q in profiles:
            if not q.get("assembler_sigma_y_pts"):
                continue
            a, b = float(q["window_m"][0]), float(q["window_m"][1])
            if b < a:
                b += lap
            by.setdefault(float(q["assembler_sigma_y_pts"]), []).append(
                (a, b, float(q.get("blend_m", PROFILE_BLEND_M))))
        self.wins = [(sig, self.sm.window_weights(st[:-1] if closed else st, lap, w)) for sig, w in sorted(by.items())]
        sigs = [self.sig_y] + [sg for sg, _w in self.wins]
        self.reach = self.ypasses * max(max(1, int(round(3.0 * sg))) for sg in sigs)

    def _chan(self, vals, sig):
        r = max(1, int(round(3.0 * sig)))
        return self.sm._smooth_channel(vals, r, self.sm._gauss_kernel(r, sig), self.ypasses, False)

    def heights(self, ys, idx):
        """the assembler's y at the contiguous vertex indices ``idx`` (exact but for ``reach`` at each end)"""
        vals = [ys[i] for i in idx]
        out = self._chan(vals, self.sig_y)
        for sig, wts in self.wins:
            w = [wts[i] for i in idx]
            if any(x > 0 for x in w):
                alt = self._chan(vals, sig)
                out = [b + x * (a - b) if x > 0 else b for a, b, x in zip(alt, out, w)]
        return out


def _ribbon(asm, ys, widths, rows, use, n, closed):
    """the ribbon the build will carry over the rows ``use``: (Pfull, N, seg, surface, triangles, pinches) — Pfull the
    predicted centreline (every row; ``rows`` with the assembler's heights), the road's two edges unfolded and
    levelled by mouth_weld exactly as the weld does; None for the surface when the weld would refuse a pinch"""
    mw, vf = _fan_tools()
    yb = asm.heights(ys, rows)
    at = dict(zip(rows, yb))
    Pfull = [(asm.plan[r][0], at.get(r, ys[r]), asm.plan[r][1]) for r in range(n)]
    if closed:
        Pfull.append(Pfull[0])
    N = vf.normals(Pfull, closed)
    seg = sorted(use)
    C = [Pfull[r] for r in seg]
    edge = {}
    for side, sg in (("L", 1.0), ("R", -1.0)):
        edge[side] = [(Pfull[r][0] + sg * N[r][0] * widths[r] / 2.0, Pfull[r][1],
                       Pfull[r][2] + sg * N[r][1] * widths[r] / 2.0) for r in seg]
    pins = []
    try:
        for side in ("L", "R"):
            rep = []
            edge[side], _d, _l = mw.unfold_line(edge[side], C, False, strict=False, level=True, report=rep)
            pins += [(q, side) for q in rep]
    except mw.WeldError as e:
        return Pfull, N, seg, None, [], [{"refused": str(e)}]
    tris = []
    Le, Re = edge["L"], edge["R"]
    for i in range(len(seg) - 1):
        tris += [(Le[i], C[i], C[i + 1], 0), (Le[i], C[i + 1], Le[i + 1], 0),
                 (C[i], Re[i], Re[i + 1], 0), (C[i], Re[i + 1], C[i + 1], 0)]
    return Pfull, N, seg, vf.Surface(tris), tris, pins


def _pinch_dt(rib, widths, closed, coarse):
    """(max DT, worst fine step, [pinch records]) of verify_fold_fans' survey over every levelled pinch of ``rib``"""
    mw, vf = _fan_tools()
    Pfull, N, seg, surf, tris, pins = rib
    if surf is None:
        return math.inf, 0.0, pins
    keep = (vf.PATH_DO_M, vf.PATH_DS_M)
    if coarse:
        vf.PATH_DO_M, vf.PATH_DS_M = FAN_SOLVE_DO_M, FAN_SOLVE_DS_M
    try:
        dt, fine, out = 0.0, 0.0, []
        lane = lambda r: (-(widths[r] / 2.0 - 0.5), widths[r] / 2.0 - 0.5)
        reach = mw.FOLD_LEVEL_ROWS + vf.WINDOW_PAD_ROWS + 14
        for q, side in pins:
            k, l = seg[0] + q["k"], seg[0] + q["l"]
            if k - reach < seg[0] or l + 1 + reach > seg[-1]:
                raise SystemExit(f"[deck] fold_fan_fit: the fold pinch at rows {k}..{l + 1} reaches past the "
                                 f"surveyed rows {seg[0]}..{seg[-1]} - widen fit_m")
            pin = {"k": k, "l": l, "X": q["X"], "y_k": q["y_k"], "y_l": q["y_l"], "lane": side}
            _f, info = vf.survey_pinch(pin, mw.FOLD_LEVEL_ROWS, Pfull, widths, N, closed, lane, surf, surf, tris,
                                       ["1ROAD_road"], lambda r: 0.0, False, None)
            dt, fine = max(dt, info["dt_max_m"]), max(fine, info["fine_max_m"])
            out.append({"rows": [k, l + 1], "side": side, "X_m": [round(q["X"][0], 2), round(q["X"][2], 2)],
                        "legs_y": [round(q["y_k"], 3), round(q["y_l"], 3)], "dt_m": round(info["dt_max_m"], 4)})
    finally:
        vf.PATH_DO_M, vf.PATH_DS_M = keep
    return dt, fine, out


def _wheels(rib, widths, lap_st, r0, r1, race_inset):
    """drive_test's own wheel paths over rows r0..r1 of ``rib`` (scripts/geometry/drive_test.py: a sample every
    STEP_M of lap station, the segment's left normal, the street's five lines clamped to the 6 m travel swath, a
    race corridor's five lines across its lane, each +- WHEEL_HALF_TRACK; kinks and severe steps on the paths that
    gate them) -> {run: [kinks, severe steps, kink excess (% pts), step excess (m)]} for the street, and when
    ``race_inset`` is given for a race lane (the full street between the edge strips: w/2 - race_inset each side)
    walked forward and in reverse"""
    from scripts.geometry import drive_test as dtm
    Pfull, _N, _seg, surf, _tris, _pins = rib
    out = {}
    if surf is None:
        return None
    runs = [("street", 1)] + ([("race", 1), ("race_reverse", -1)] if race_inset is not None else [])
    L = lap_st[-1]
    for name, sgn in runs:
        ks = []
        a, b = lap_st[r0], lap_st[r1]
        if sgn > 0:
            k = math.ceil(a / dtm.STEP_M)
            while k * dtm.STEP_M <= b:
                ks.append(k * dtm.STEP_M)
                k += 1
        else:
            k = math.ceil((L - b) / dtm.STEP_M)
            while L - k * dtm.STEP_M >= a:
                ks.append(L - k * dtm.STEP_M)
                k += 1
        res = [0, 0, 0.0, 0.0]
        prev_h = [None] * 10
        prev_slope = [None] * 10
        i = r0 + 1
        for s in ks:
            i = r0 + 1
            while i < r1 and lap_st[i] < s:
                i += 1
            t = (s - lap_st[i - 1]) / max(lap_st[i] - lap_st[i - 1], 1e-9)
            p0, p1 = Pfull[i - 1], Pfull[i]
            x, z = p0[0] + (p1[0] - p0[0]) * t, p0[2] + (p1[2] - p0[2]) * t
            tx, tz = p1[0] - p0[0], p1[2] - p0[2]
            Ln = math.hypot(tx, tz) or 1e-9
            nx, nz = -tz / Ln, tx / Ln
            w = widths[i]
            if name == "street":
                lines = (-(w / 2 - 0.5), -w / 3, 0.0, w / 3, (w / 2 - 0.5))
                cc, cr = 0.0, min(max(w / 2 - 0.4, 0.8), 6.0)
                edge = {0, 4}
            else:
                half = w / 2.0 - race_inset - dtm.DIVIDER_CLEAR_M - dtm.WHEEL_HALF_TRACK
                third = 2.0 * half / 3.0
                lines = (-half, -third / 2, 0.0, third / 2, half)
                cc, cr = 0.0, half
                edge = set()
            paths = [off + d for off in lines for d in (-dtm.WHEEL_HALF_TRACK, dtm.WHEEL_HALF_TRACK)]
            for pi, off in enumerate(paths):
                if abs(off - cc) > cr:
                    off = cc + math.copysign(cr, off - cc)
                h, _own = surf.top(x + nx * off, z + nz * off)
                if h is None:
                    prev_h[pi] = prev_slope[pi] = None
                    continue
                if prev_h[pi] is not None:
                    slope = (h - prev_h[pi]) / dtm.STEP_M
                    if prev_slope[pi] is not None and (pi // 2) not in edge:
                        kink = abs(slope - prev_slope[pi]) * 100
                        if kink > dtm.KINK_PCT:
                            res[0] += 1
                            res[2] += kink - dtm.KINK_PCT
                        step = abs(slope - prev_slope[pi]) * dtm.STEP_M
                        if step > dtm.STEP_SEVERE_M:
                            res[1] += 1
                            res[3] += step - dtm.STEP_SEVERE_M
                    prev_slope[pi] = slope
                prev_h[pi] = h
        out[name] = res
    return out


def fan_taper(s, f0, f1):
    """1 inside fit_m, a smoothstep to 0 over FAN_TAPER_M at both ends, 0 outside"""
    w = min(1.0, (s - f0) / FAN_TAPER_M, (f1 - s) / FAN_TAPER_M)
    return 0.0 if w <= 0 else w * w * (3 - 2 * w)


def fit_fold_fan(p, asm, pts, st, widths, ys, window, cache=None, cache_p=None, ys_before=None):
    """the fold-fan fit of profile ``p`` (see the section doc): returns (new ys, report record). The solved bump
    amplitudes are cached in data/deck_datum.samples.json under fold_fan_fits, keyed by the md5 of everything the
    solve reads (heights, plan and widths of the surveyed rows, the assembler's sigmas, every FAN_ constant): a hit
    skips the descent (minutes) and is re-surveyed in full like a fresh solve. ``ys_before``: the line before this
    profile window (the frozen profile): its build, as v0.18.0 built it (the assembler's route sigma, no window), is
    the baseline drive_test's wheel paths may not get worse than"""
    spec = p["fold_fan_fit"]
    w0, w1, blend = window
    f0, f1 = (float(v) for v in spec["fit_m"])
    if not (w0 + blend <= f0 < f1 <= w1 - blend):
        raise SystemExit(f"[deck] profile {p['name']}: fold_fan_fit.fit_m {spec['fit_m']} must lie inside the window "
                         f"past its blend ({blend} m)")
    dt_max = float(spec.get("dt_max_m", FAN_DT_MAX_M))
    closed = abs(pts[0][0] - pts[-1][0]) < 1e-6 and abs(pts[0][2] - pts[-1][2]) < 1e-6
    n = len(pts) - 1 if closed else len(pts)
    fit = [i for i in range(n) if f0 <= st[i] <= f1]
    use = set(range(fit[0] - FAN_PAD_ROWS, fit[-1] + FAN_PAD_ROWS + 1))
    rows = list(range(fit[0] - FAN_PAD_ROWS - asm.reach, fit[-1] + FAN_PAD_ROWS + asm.reach + 1))
    if rows[0] < 0 or rows[-1] >= n:
        raise SystemExit(f"[deck] profile {p['name']}: fold_fan_fit.fit_m too close to the lap seam")
    cs = []
    c = f0 + FAN_BUMP_SPACING_M / 2.0
    while c < f1:
        cs.append(c)
        c += FAN_BUMP_SPACING_M

    basis = [[fan_taper(st[i], f0, f1) * math.exp(-((st[i] - cj) ** 2) / (2 * FAN_BUMP_SIGMA_M ** 2)) for i in fit]
             for cj in cs]
    tgt_b = asm.heights(ys, fit)
    evals = [0]
    ds = [max(1e-6, lap_d) for lap_d in (math.hypot(asm.plan[i + 1][0] - asm.plan[i][0],
                                                   asm.plan[i + 1][1] - asm.plan[i][1]) for i in fit[:-1])]

    def misfit(hb):
        """m^2: the built heights', grades' and grade changes' distance from the 3DEP target's
        (FAN_GRADE_WEIGHT_M2 per grade^2, FAN_BEND_WEIGHT_M2 per (grade change per vertex)^2)"""
        e = sum((h - t_) ** 2 for h, t_ in zip(hb, tgt_b))
        dg = [((hb[j + 1] - hb[j]) - (tgt_b[j + 1] - tgt_b[j])) / ds[j] for j in range(len(ds))]
        g = sum(x * x for x in dg)
        c = sum((dg[j + 1] - dg[j]) ** 2 for j in range(len(dg) - 1))
        return e + FAN_GRADE_WEIGHT_M2 * g + FAN_BEND_WEIGHT_M2 * c
    # drive_test's wheel paths over the fit (street; a race lane when the track declares race furniture): no severe
    # step at all (each one is a drive_test failure), and never more kinks, nor more kink excess, than the frozen
    # profile had here as v0.18.0 built it (kinks are a per-km rate the whole lap shares)
    race = asm.cfg.get("race") or {}
    race_inset = float(race.get("edge_inset_m", 0.82)) if any(lo.get("race_furniture") for lo in
                                                              asm.cfg.get("layouts") or []) else None
    lap_st = [0.0]
    for r in range(1, n + (1 if closed else 0)):
        a_, b_ = asm.plan[r - 1], asm.plan[r % len(asm.plan)]
        lap_st.append(lap_st[-1] + math.hypot(b_[0] - a_[0], b_[1] - a_[1]))
    wr0, wr1 = fit[0] - FAN_WHEEL_PAD_ROWS, fit[-1] + FAN_WHEEL_PAD_ROWS
    base_asm = _Assembler(asm.cfg, [], pts, st, closed)
    wb = _wheels(_ribbon(base_asm, list(ys_before if ys_before is not None else ys), widths, rows, use, n, closed),
                 widths, lap_st, wr0, wr1, race_inset)
    if wb is None:
        raise SystemExit(f"[deck] profile {p['name']}: fold_fan_fit: the weld refuses the frozen profile's own fan")

    def wheel_over(w):
        if w is None:
            return math.inf
        o = 0.0
        for run, (k_, s_, kx, sx) in w.items():
            kb, _sb, kxb, _sxb = wb[run]
            o += max(0, k_ - kb) + s_ + 0.1 * max(0.0, kx - kxb) + 10.0 * sx
        return o

    def shaped(a):
        out = list(ys)
        for j, i in enumerate(fit):
            out[i] = ys[i] + sum(aj * bj[j] for aj, bj in zip(a, basis) if aj)
        return out

    def cost(a):
        evals[0] += 1
        y2 = shaped(a)
        rib = _ribbon(asm, y2, widths, rows, use, n, closed)
        dt, fine, _pins = _pinch_dt(rib, widths, closed, True)
        if math.isinf(dt):
            return math.inf, dt
        wo = wheel_over(_wheels(rib, widths, lap_st, wr0, wr1, race_inset))
        over = max(0.0, dt - dt_solve) + (1.0 if fine > 0.0 else 0.0)
        return misfit(asm.heights(y2, fit)) + FAN_PENALTY * over * over + FAN_COUNT_PENALTY * wo, dt

    dt_solve = dt_max - FAN_COARSE_MARGIN_M
    key = hashlib.md5(json.dumps({
        "ys": [round(ys[r], 4) for r in rows], "before": [round(v, 4) for v in (ys_before or ys)[rows[0]:rows[-1] + 1]],
        "race_inset": race_inset, "plan": [[round(asm.plan[r][0], 3), round(asm.plan[r][1], 3)] for r in rows],
        "w": [round(float(widths[r]), 3) for r in rows], "fit": [f0, f1, dt_max], "sig_y": asm.sig_y,
        "wins": [[sg, [round(w[r], 4) for r in rows]] for sg, w in asm.wins],
        "const": [FAN_BUMP_SPACING_M, FAN_BUMP_SIGMA_M, FAN_TAPER_M, FAN_STEP0_M, FAN_STEP_MIN_M, FAN_PENALTY,
                  FAN_SOLVE_DO_M, FAN_SOLVE_DS_M, FAN_COARSE_MARGIN_M, FAN_PAD_ROWS, FAN_WHEEL_PAD_ROWS,
                  FAN_COUNT_PENALTY, FAN_GRADE_WEIGHT_M2, FAN_BEND_WEIGHT_M2]}, sort_keys=True).encode()).hexdigest()
    store = (cache or {}).setdefault("fold_fan_fits", {}) if cache is not None else {}
    hit = store.get(key)
    a = [0.0] * len(cs)
    rib0 = _ribbon(asm, ys, widths, rows, use, n, closed)
    dt0_full, _f0, pins0 = _pinch_dt(rib0, widths, closed, False)
    w0_ = _wheels(rib0, widths, lap_st, wr0, wr1, race_inset)
    if hit and len(hit.get("amplitudes_m") or []) == len(cs):
        a = [float(x) for x in hit["amplitudes_m"]]
        best = cost(a)
        print(f"[deck] profile {p['name']}: fold-fan fit cached (key {key[:12]}), re-surveyed")
    else:
        best = cost(a)
        hit = None
    step = FAN_STEP0_M
    if hit is None and best[1] > dt_solve:
        while step >= FAN_STEP_MIN_M - 1e-12 and evals[0] < FAN_MAX_EVALS:
            moved = False
            for j in range(len(a)):
                for sg in (1.0, -1.0):
                    b = list(a)
                    b[j] += sg * step
                    v = cost(b)
                    if v[0] < best[0] - 1e-12:
                        a, best, moved = b, v, True
                        break
            if not moved:
                step /= 2.0
    y2 = shaped(a)
    dt_c = best[1]
    rib2 = _ribbon(asm, y2, widths, rows, use, n, closed)
    dt_full, fine_full, pins = _pinch_dt(rib2, widths, closed, False)
    w2 = _wheels(rib2, widths, lap_st, wr0, wr1, race_inset)
    _mw, vf = _fan_tools()
    if wheel_over(w2) > 0.0:
        raise SystemExit(f"[deck] profile {p['name']}: fold_fan_fit cannot carry the profile past drive_test's wheel "
                         f"paths (kinks / severe steps / their excess per run {w2}; the frozen profile's {wb}; no "
                         f"severe step, no more kinks) "
                         f"- author the junction as a pad (JUNCTIONS 2.0 B)")
    if dt_c > dt_solve + 1e-9 or dt_full > dt_max + 1e-9 or dt_full > vf.DT_MAX_M or fine_full > 0.0:
        raise SystemExit(f"[deck] profile {p['name']}: fold_fan_fit cannot carry the profile through its fold fan "
                         f"(DT {dt_c:.4f} m solver against {dt_solve:.3f} / {dt_full:.4f} m full survey against "
                         f"{dt_max}, the gate's {vf.DT_MAX_M}; fine step {fine_full:.3f}) - author the junction as a "
                         f"pad (JUNCTIONS 2.0 B)")
    hb = asm.heights(y2, fit)
    dy = [h - t for h, t in zip(hb, tgt_b)]
    if max(abs(x) for x in dy) > FAN_MAX_MOVE_M:
        raise SystemExit(f"[deck] profile {p['name']}: fold_fan_fit moved a built height {max(dy, key=abs):+.3f} m "
                         f"from the 3DEP target (> {FAN_MAX_MOVE_M} m) - author the junction as a pad "
                         f"(JUNCTIONS 2.0 B)")
    if cache is not None and cache_p is not None and store.get(key, {}).get("amplitudes_m") != [round(x, 4) for x in a]:
        store[key] = {"profile": p["name"], "amplitudes_m": [round(x, 4) for x in a], "evals": evals[0],
                      "dt_after_m": round(dt_full, 4),
                      "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        cache_p.write_text(json.dumps(cache, separators=(",", ":")), encoding="utf-8")
    rec = {"fit_m": [f0, f1], "dt_max_m": dt_max, "dt_solve_m": round(dt_solve, 4), "bumps": len(cs),
           "evals": evals[0], "cache_key": key, "cached": hit is not None,
           "dt_before_m": round(dt0_full, 4), "dt_after_m": round(dt_full, 4), "dt_after_solver_m": round(dt_c, 4),
           "pinches_before": pins0, "pinches": pins,
           "wheel_paths": {"_doc": "drive_test's wheel paths over fit_m +- FAN_WHEEL_PAD_ROWS: [kinks, severe steps, "
                                   "kink excess % pts, step excess m] per run", "frozen_profile_v0180": wb,
                           "unfitted": w0_, "fitted": w2},
           "built_change_m": {"max_raise": round(max(dy), 3), "max_lower": round(min(dy), 3),
                              "rms": round(math.sqrt(sum(d * d for d in dy) / len(dy)), 3)},
           "amplitudes_m": [round(x, 3) for x in a]}
    print(f"[deck] profile {p['name']}: fold-fan fit over {f0:.0f}-{f1:.0f} m - fan DT {dt0_full:.3f} -> "
          f"{dt_full:.3f} m (gate {vf.DT_MAX_M}, fit to {dt_max}); the built profile moves +{max(dy):.3f} / "
          f"{min(dy):.3f} m (rms {rec['built_change_m']['rms']:.3f}) in {evals[0]} evaluations")
    return y2, rec


def _md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def _apply_profiles(profiles, decks, raw, pts, st, ys, cache, cache_p, offline, geo, report, cfg=None):
    """every road_datum.profiles window onto ``ys`` (see the module doc); returns the new heights"""
    o, m_lon, m_lat = geo
    elev0 = float(o["elev_m"])
    widths = raw.get("widths_m") or [10.0] * len(pts)
    L = st[-1]
    closed = abs(pts[0][0] - pts[-1][0]) < 1e-6 and abs(pts[0][2] - pts[-1][2]) < 1e-6
    ring = len(pts) - 1 if closed else len(pts)
    margin = 3.0 * PROFILE_SIGMA_M + SMOOTH_M
    # where the 3DEP is read. Inside a fold-fan fit's fit_m: on the plan the assembler will BUILD (its own plan
    # smoothing of this line, index-aligned, so vertex i's height is read where vertex i will stand) — round the
    # College/Alvarado hairpin that smoothing moves the line up to 3.6 m and the junction tilts 8 % across, so read on
    # the pre-median plan the slab sat 0.1-0.3 m off the real road under the built one (ledger 0057 fix round). A
    # median never reaches a fold fan (median_envelope ends every run short of a junction), so there the prediction is
    # the built plan; elsewhere the pre-median plan as before (median_envelope moves divided roads after this step).
    fits = [q for q in profiles if q.get("fold_fan_fit")]
    asm = None
    ref = pts
    if fits:
        if not (cfg or {}).get("road_datum", {}).get("assembler_smooth"):
            raise SystemExit("[deck] fold_fan_fit needs road_datum.assembler_smooth (the assembler's smooth.py, "
                             "relative to the airoso repo) to predict the ribbon it judges")
        asm = _Assembler(cfg, profiles, pts, st, closed)
        ref = [list(q) for q in pts]
        for q in fits:
            f0, f1 = (float(v) for v in q["fold_fan_fit"]["fit_m"])
            for i in range(len(pts)):
                w = fan_taper(st[i], f0, f1)
                if w > 0:
                    ref[i][0] = pts[i][0] + w * (asm.plan[i][0] - pts[i][0])
                    ref[i][2] = pts[i][2] + w * (asm.plan[i][1] - pts[i][2])
    for p in profiles:
        w0, w1 = unwrap_window(p["window_m"], L)
        if not closed and w1 > L:
            raise SystemExit(f"[deck] profile {p['name']}: a window through the seam needs a closed line")
        blend = float(p.get("blend_m", PROFILE_BLEND_M))
        if w1 - w0 < 2 * blend or w1 - w0 > L - 2 * margin:
            raise SystemExit(f"[deck] profile {p['name']}: window {p['window_m']} must be at least twice its blend "
                             f"({blend} m) and shorter than the lap")
        spans = window_spans(decks, w0, w1, L)
        spans.sort()
        ts = profile_samples(w0, w1)
        lr = carriageway_centres(ref, st, widths, ts)
        keys = [(f"{a[0]:.2f},{a[1]:.2f}", f"{b[0]:.2f},{b[1]:.2f}") for a, b in lr]
        need = {}
        for (ka, kb), (a, b) in zip(keys, lr):
            for k, xz in ((ka, a), (kb, b)):
                if k not in cache["points"]:
                    need[k] = xz
        if need:
            if offline:
                raise SystemExit(f"[deck] profile {p['name']}: {len(need)} 3DEP samples not cached and --offline")
            from scripts.elevation import terrain_sample as ts_mod
            items = sorted(need.items())
            ll = [(o["lon"] + x / m_lon, o["lat"] + z / m_lat) for _k, (x, z) in items]
            vals = ts_mod.sample_lonlat(ll, f"profile {p['name']}")
            for (k, _xz), v in zip(items, vals):
                cache["points"][k] = v
            cache["_provenance"]["fetches"].append({"utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                                                    "points": len(need), "what": f"profile {p['name']} (both "
                                                    f"carriageway centres, +-width/4)"})
            cache_p.write_text(json.dumps(cache, separators=(",", ":")), encoding="utf-8")
        dep = [(cache["points"][ka] + cache["points"][kb]) / 2.0 - elev0 for ka, kb in keys]
        tgt, held = profile_target(ts, dep, [(a, b) for a, b, _n in spans], PROFILE_SIGMA_M)
        us = [unwrapped(st[i], w0, w1, L) for i in range(ring)] + ([None] if closed else [])
        old = list(ys)
        ys = apply_profile(us, ys, ts, tgt, w0, w1, blend)
        if closed:
            ys[-1] = ys[0]          # the closing duplicate is v0, never a second vertex (L13)
        fit = None
        if p.get("fold_fan_fit"):
            # ledger 0057 fix round: the profile as close to 3DEP as the levelled fold fan inside it can carry
            ys, fit = fit_fold_fan(p, asm, pts, st, widths, ys, (w0, w1, blend), cache, cache_p, ys_before=old)
            if closed:
                ys[-1] = ys[0]
        order = sorted((u, i) for i, u in enumerate(us) if u is not None)
        moved = [(round(st[i], 1), round(ys[i] - old[i], 3)) for _u, i in order if abs(ys[i] - old[i]) > 1e-6]
        grades = [(ys[j] - ys[i]) / max(1e-6, u1 - u0) for (u0, i), (u1, j) in zip(order, order[1:])]
        rec = {"name": p["name"], "window_m": [float(p["window_m"][0]), float(p["window_m"][1])],
               "unwrapped_m": [round(w0, 1), round(w1, 1)], "blend_m": blend, "sigma_m": PROFILE_SIGMA_M,
               "assembler_sigma_y_pts": p.get("assembler_sigma_y_pts"), "why": p.get("why", ""),
               "spans_held": [{"deck": n, "deck_m": [round(a % L, 1), round(b % L, 1)],
                               "abutment_heights_abs_m": [round(ya + elev0, 2), round(yb + elev0, 2)],
                               "deck_grade_pct": round(100 * (yb - ya) / (b - a), 2)}
                              for (a, b, n), (ya, yb) in zip(spans, held)],
               "vertices_moved": len(moved), "max_raise_m": round(max([m for _s, m in moved] or [0.0]), 3),
               "max_lower_m": round(min([m for _s, m in moved] or [0.0]), 3),
               "max_grade_pct": round(100 * max(abs(g) for g in grades), 2) if grades else 0.0,
               "max_grade_change_pct": round(100 * max([abs(g1 - g0) for g0, g1 in zip(grades, grades[1:])] or [0.0]),
                                             2),
               "moves": moved}
        if fit is not None:
            rec["fold_fan_fit"] = fit
        report["profiles"].append(rec)
        print(f"[deck] profile {p['name']}: {w0:.0f}-{w1 % L:.0f} m (blend {blend:.0f} m, 3DEP at both carriageway "
              f"centres, sigma {PROFILE_SIGMA_M} m; spans held: {', '.join(n for _a, _b, n in spans) or 'none'}), "
              f"{len(moved)} vertices moved (raise <= {rec['max_raise_m']} m, lower <= {-rec['max_lower_m']} m), "
              f"grade <= {rec['max_grade_pct']} %, grade change <= {rec['max_grade_change_pct']} % per vertex")
    return ys


def run(proj: Path, offline: bool = False) -> dict | None:
    data = proj / "data"
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    decks = (cfg.get("road_datum") or {}).get("decks") or []
    if not decks and not (cfg.get("road_datum") or {}).get("profiles"):
        print("[deck] no road_datum.decks or road_datum.profiles declared — nothing to do")
        return None
    src = data / SRC_NAME
    if not src.exists():
        raise SystemExit(f"[deck] {src} missing (the ship chain syncs it from tracks/<slug>/data)")
    rep_p = data / "deck_datum.json"
    if rep_p.exists():
        prev = json.loads(rep_p.read_text(encoding="utf-8"))
        if prev.get("output_md5") == _md5(src):
            print(f"[deck] {SRC_NAME} already carries the corrected decks (md5 {prev['output_md5']}) — unchanged")
            return prev
    raw = json.loads(src.read_text(encoding="utf-8"))
    pts = [list(p) for p in raw["points_xyz_m"]]
    o = raw["origin"]
    elev0 = float(o["elev_m"])
    from scripts.geometry import terrain_tiers as tt
    m_lon, m_lat = tt.meters_per_degree(o["lat"])
    st = stations(pts)
    cache_p = data / "deck_datum.samples.json"
    cache = json.loads(cache_p.read_text(encoding="utf-8")) if cache_p.exists() else {
        "_provenance": {"source": "USGS 3DEP 1 m bare earth, ImageServer getSamples (returnFirstValueOnly)",
                        "units": "metres above NAVD88", "along": f"data/{SRC_NAME} (plan positions), every "
                        f"{SAMPLE_M} m", "fetches": []}, "points": {}}
    in_md5 = _md5(src)
    report = {"_doc": "tools/deck_datum.py — real bridge decks between real abutments (LAWS L3; ledger 0046 v0.18.0 "
                      "integration fix round)", "input": SRC_NAME, "input_md5": in_md5, "decks": []}
    ys = [p[1] for p in pts]
    profiles = (cfg.get("road_datum") or {}).get("profiles") or []
    for d in decks:
        w0, w1 = (float(v) for v in d["window_m"])
        a, b = (float(v) for v in d["deck_m"])
        if not (w0 + BLEND_M <= a < b <= w1 - BLEND_M):
            raise SystemExit(f"[deck] {d['name']}: deck {d['deck_m']} must sit inside window {d['window_m']} "
                             f"by {BLEND_M} m")
        inside = [pr["name"] for pr in profiles
                  if any(n == d["name"] for _a, _b, n in window_spans(decks, *unwrap_window(pr["window_m"], st[-1]),
                                                                       st[-1]))]
        if inside:
            # a deck inside a profile window is held straight BY the profile (its span, on the profile's own 3DEP);
            # its own window pass would only blend into the old profile the window replaces
            report["decks"].append({"name": d["name"], "window_m": [w0, w1], "deck_m": [a, b], "why": d.get("why", ""),
                                    "re_derived_by_profile": inside[0]})
            print(f"[deck] {d['name']}: deck {a:.0f}-{b:.0f} m lies inside profile {inside[0]} - held straight there")
            continue
        ts = [w0 + k * SAMPLE_M for k in range(int(round((w1 - w0) / SAMPLE_M)) + 1)]
        xz = [point_at(pts, st, t) for t in ts]
        keys = [f"{x:.2f},{z:.2f}" for x, z in xz]
        need = [(k, xzk) for k, xzk in zip(keys, xz) if k not in cache["points"]]
        if need:
            if offline:
                raise SystemExit(f"[deck] {d['name']}: {len(need)} 3DEP samples not cached and --offline")
            from scripts.elevation import terrain_sample as ts_mod
            ll = [(o["lon"] + x / m_lon, o["lat"] + z / m_lat) for _k, (x, z) in need]
            vals = ts_mod.sample_lonlat(ll, f"deck {d['name']}")
            for (k, _xz), v in zip(need, vals):
                cache["points"][k] = v
            cache["_provenance"]["fetches"].append({"utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                                                    "points": len(need), "what": d["name"]})
            cache_p.write_text(json.dumps(cache, separators=(",", ":")), encoding="utf-8")
        dep = [cache["points"][k] - elev0 for k in keys]
        tgt, ya, yb = target_profile(ts, dep, (a, b))
        old = list(ys)
        ys = apply_deck(st, ys, ts, tgt, (w0, w1))
        moved = [(round(s, 1), round(n - q, 3)) for s, n, q in zip(st, ys, old) if abs(n - q) > 1e-6]
        # grades along the corrected window (for the report; the assembler's smoothing runs on top)
        idx = [i for i, s in enumerate(st) if w0 - 10 <= s <= w1 + 10]
        grades = [(ys[i + 1] - ys[i]) / max(1e-6, st[i + 1] - st[i]) for i in idx[:-1]]
        rec = {"name": d["name"], "window_m": [w0, w1], "deck_m": [a, b], "why": d.get("why", ""),
               "abutment_heights_abs_m": [round(ya + elev0, 2), round(yb + elev0, 2)],
               "deck_grade_pct": round(100 * (yb - ya) / (b - a), 2),
               "vertices_moved": len(moved), "max_raise_m": round(max([m for _s, m in moved] or [0.0]), 3),
               "max_lower_m": round(min([m for _s, m in moved] or [0.0]), 3),
               "max_grade_pct": round(100 * max(abs(g) for g in grades), 2),
               "max_grade_change_pct": round(100 * max(abs(g1 - g0) for g0, g1 in zip(grades, grades[1:])), 2),
               "moves": moved}
        report["decks"].append(rec)
        print(f"[deck] {d['name']}: deck {a:.0f}-{b:.0f} m held straight {rec['abutment_heights_abs_m'][0]} -> "
              f"{rec['abutment_heights_abs_m'][1]} m ({rec['deck_grade_pct']} %), {len(moved)} vertices moved "
              f"(raise <= {rec['max_raise_m']} m, lower <= {-rec['max_lower_m']} m), grade <= {rec['max_grade_pct']} %, "
              f"grade change <= {rec['max_grade_change_pct']} % per vertex")
    if profiles:
        report["_doc"] += "; profile windows (ledger 0057)"
        report["profiles"] = []
        ys = _apply_profiles(profiles, decks, raw, pts, st, ys, cache, cache_p, offline, (o, m_lon, m_lat), report,
                             cfg)
    for p, y in zip(raw["points_xyz_m"], ys):
        p[1] = round(y, 4)
    src.write_text(json.dumps(raw), encoding="utf-8")
    report["output_md5"] = _md5(src)
    rep_p.write_text(json.dumps(report, indent=1), encoding="utf-8")
    return report


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        raise SystemExit("usage: python tools/deck_datum.py <project-dir> [--offline]")
    run(Path(args[0]), offline="--offline" in sys.argv)


if __name__ == "__main__":
    main()

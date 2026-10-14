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
existing profile over the window's blend_m at both ends. A window's hold_straight_m spans (a junction box the build
cannot warp — a levelled fold fan, ledger 0050) are held straight between the road at their edges the same way. Decks
run first, profiles second: a deck inside a profile is held straight by the profile (its own window pass is skipped
and reported re_derived_by_profile), a deck outside every profile is exactly as before. The road
stays a level slab across its width (the real junction's 4-7 % cross-tilt is not carried — ledger 0057 Fix).
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


def _md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def _apply_profiles(profiles, decks, raw, pts, st, ys, cache, cache_p, offline, geo, report):
    """every road_datum.profiles window onto ``ys`` (see the module doc); returns the new heights"""
    o, m_lon, m_lat = geo
    elev0 = float(o["elev_m"])
    widths = raw.get("widths_m") or [10.0] * len(pts)
    L = st[-1]
    closed = abs(pts[0][0] - pts[-1][0]) < 1e-6 and abs(pts[0][2] - pts[-1][2]) < 1e-6
    ring = len(pts) - 1 if closed else len(pts)
    margin = 3.0 * PROFILE_SIGMA_M + SMOOTH_M
    for p in profiles:
        w0, w1 = unwrap_window(p["window_m"], L)
        if not closed and w1 > L:
            raise SystemExit(f"[deck] profile {p['name']}: a window through the seam needs a closed line")
        blend = float(p.get("blend_m", PROFILE_BLEND_M))
        if w1 - w0 < 2 * blend or w1 - w0 > L - 2 * margin:
            raise SystemExit(f"[deck] profile {p['name']}: window {p['window_m']} must be at least twice its blend "
                             f"({blend} m) and shorter than the lap")
        spans = window_spans(decks, w0, w1, L)
        # a junction box the build cannot warp (a levelled fold fan, ledger 0050) is held straight like a span
        for k, (a, b) in enumerate(p.get("hold_straight_m") or []):
            A, B = (float(a), float(b))
            if B < A:
                B += L
            if A < w0:
                A, B = A + L, B + L
            if not (w0 + blend <= A < B <= w1 - blend):
                raise SystemExit(f"[deck] profile {p['name']}: hold_straight_m {[a, b]} must lie inside the window "
                                 f"past its blend ({blend} m)")
            spans.append((A, B, f"hold:{p['name']}#{k}"))
        spans.sort()
        ts = profile_samples(w0, w1)
        lr = carriageway_centres(pts, st, widths, ts)
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
        ys = _apply_profiles(profiles, decks, raw, pts, st, ys, cache, cache_p, offline, (o, m_lon, m_lat), report)
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

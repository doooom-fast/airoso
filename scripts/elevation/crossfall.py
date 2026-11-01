"""Measure REAL road cross-slope (camber/superelevation) from the 1 m USGS 3DEP DEM.

Samples the DEM in LATERAL PAIRS — a point near each pavement edge, every ~6 m along the lap —
and converts the height difference into a signed cross-slope. On a mountain road this recovers
the real superelevation pattern Kevin described: banked into the hillside through many curves
(outer/valley edge higher), flat elsewhere.

Safety over drama (the previous attempts "ended up super high" and launched cars):
  - DEADBAND: |slope| < 1.5% -> 0. DEM noise over a ~5 m baseline is ±2-3% per raw sample; only a
    sustained signal survives the median, and mild readings stay flat ("...but not everywhere").
  - CAP: ±6% (~3.4 deg) — the real rural superelevation maximum. Never hairpin-bowl banking.
  - RUNOFF: median (window ~54 m) then mean (~30 m) smoothing along-track, so banking rotates in
    gradually like a real superelevation transition, never snaps.

Writes data/crossfall.json: {"station_m": [...], "bank_rad": [...]} — positive = LEFT edge up
(matches the ribbon/bank_at convention). build_mesh consumes it when the track has no
hand-authored road_profile.cambers.

Run:  python -m scripts.elevation.crossfall tracks/<slug>

FOOTPRINT MODE (opt-in: ``road_profile.crossfall.method = "footprint"`` in track.config.json; the Lariat V3,
ledger 0048, V3-PLAN P2 step 4). ``build`` above is unchanged for every track that does not opt in. On a 6 m
mountain road a lateral pair at the pavement edge reads the cut or the fill, not the road (L3b), and the July
Lariat file read 10 % of its stations at the 6 % cap and swung >= 3 % each way within 30 m in 9 places.
``build_footprint`` instead:
  - samples 3DEP across the REAL-WIDTH footprint only (``centerline.local.json`` widths, after the measured-widths
    stage): offsets 0, +-(w/2 - EDGE_IN_M)/2 and +-(w/2 - EDGE_IN_M), every STEP_M along the lap, in the LOCAL
    frame (the stations every V3 tool keys on), and fits the plane tilt (least squares) plus a crown term;
  - samples the ground beside the road (w/2 + 2, 5, 8 m) only to CLASSIFY the section: a bench (cut on one side)
    or not. Those samples never enter a tilt;
  - fills with the construction standard (docs/ROAD-CONSTRUCTION.md "Drainage"): a 2 % crown, or 2 % toward the
    cut ditch on a bench. A measured tilt is kept only where it is stronger than the standard's own 2 % (a 2 %
    crown is 4 cm over 2 m: the 1 m DEM cannot resolve it), within the 6 % public-road cap, not banked into a
    curve (A6 / L10: tilting INTO a curve by more than the standard's 2 %), and its stretch passes the roll-rate
    gate; every failing stretch takes the standard. Declared decks (data/bridge.spans.json) always take the
    standard (the DEM under a deck is what it spans);
  - ramps every change at RUNOFF_RATE (0.12 % per metre) on each half of the section, so the written
    file passes the roll-rate gate by construction (the gate still runs on it);
  - writes data/crossfall.json with ``status: "estimated"`` (until a 3DEP source-lidar sample agrees, REALISM
    section 5), the legacy keys (``station_m``, ``bank_rad`` = the plane tilt, + = left edge up) and per station
    ``left_pct`` / ``right_pct`` (each half's cross-slope, + = its left side higher: a 2 % crown is -2 / +2),
    ``crown_pct``, ``kind`` (crown / bench_left / bench_right / measured / deck) and the raw measurement.
The roll-rate gate (``roll_rate_check``; ``tools/verify_crossfall.py`` runs it on the written file): on each half
of the section, the tilt changes by <= 4 % within any 30 m, and never swings from >= +3 % to <= -3 % within 30 m
(both [invented], V3-PLAN P5; fleet/GATES-CHANGELOG.md).
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from scripts.elevation.usgs_3dep import sample_points

DEADBAND = 0.015
CAP = 0.06
STRIDE = 2                # sample every 2nd centerline vertex (~6 m)
EDGE_INSET = 0.6          # sample this far inside each pavement edge


def build(project_dir: str | Path) -> dict:
    project = Path(project_dir)
    data = project / "data"
    gj = json.loads((data / "centerline.geojson").read_text())
    feat = next(f for f in gj["features"] if f["properties"].get("kind") == "full")
    cs = [(c[0], c[1]) for c in feat["geometry"]["coordinates"]]
    widths = feat["properties"].get("widths_m") or [7.0] * len(cs)
    lc = json.loads((data / "centerline.local.json").read_text())
    if len(lc["widths_m"]) == len(cs):
        widths = lc["widths_m"]                    # post-widths-pass values

    lat0 = sum(p[1] for p in cs) / len(cs)
    m_lon = 111_320.0 * math.cos(math.radians(lat0))
    m_lat = 110_540.0

    idx = list(range(1, len(cs) - 1, STRIDE))
    pairs = []
    baselines = []
    for i in idx:
        (lo0, la0), (lo1, la1) = cs[i - 1], cs[i + 1]
        tx, tz = (lo1 - lo0) * m_lon, (la1 - la0) * m_lat
        L = math.hypot(tx, tz) or 1e-9
        nx, nz = -tz / L, tx / L                   # left normal in metres
        half = max(widths[i] / 2.0 - EDGE_INSET, 1.5)
        pairs.append((cs[i][0] + nx * half / m_lon, cs[i][1] + nz * half / m_lat))    # left
        pairs.append((cs[i][0] - nx * half / m_lon, cs[i][1] - nz * half / m_lat))    # right
        baselines.append(2 * half)
    zs = sample_points(pairs)

    raw = []
    for k in range(len(idx)):
        zl, zr = zs[2 * k], zs[2 * k + 1]
        raw.append((zl - zr) / baselines[k])       # +ve = left edge up

    def med(a, w):
        h = w // 2
        return [sorted(a[max(0, i - h):i + h + 1])[len(a[max(0, i - h):i + h + 1]) // 2]
                for i in range(len(a))]

    def mean(a, w):
        h = w // 2
        return [sum(a[max(0, i - h):i + h + 1]) / len(a[max(0, i - h):i + h + 1])
                for i in range(len(a))]

    sm = mean(med(raw, 9), 5)                       # ~54 m median + ~30 m mean at 6 m stride
    banked = 0
    out_bank = []
    for v in sm:
        if abs(v) < DEADBAND:
            out_bank.append(0.0)
        else:
            s = max(-CAP, min(CAP, v))
            out_bank.append(math.atan(s))
            banked += 1

    # stations along the lap for the sampled indices
    def hav(a, b):
        r = 6_371_000.0
        (lo1, la1), (lo2, la2) = a, b
        p1, p2 = math.radians(la1), math.radians(la2)
        dp, dl = math.radians(la2 - la1), math.radians(lo2 - lo1)
        h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
        return 2 * r * math.asin(math.sqrt(h))

    st = [0.0]
    for i in range(1, len(cs)):
        st.append(st[-1] + hav(cs[i - 1], cs[i]))
    stations = [round(st[i], 1) for i in idx]

    out = {"station_m": stations, "bank_rad": [round(b, 5) for b in out_bank],
           "deadband": DEADBAND, "cap": CAP,
           "banked_pct": round(100 * banked / max(1, len(out_bank)), 1),
           "max_bank_pct": round(100 * math.tan(max(abs(b) for b in out_bank)), 2) if out_bank else 0}
    (data / "crossfall.json").write_text(json.dumps(out), encoding="utf-8")
    print(f"crossfall: {len(stations)} stations, {out['banked_pct']}% of lap banked, "
          f"max {out['max_bank_pct']}% cross-slope (cap {CAP*100:.0f}%)")
    return out


# =============================================================================================================
# FOOTPRINT MODE (opt-in per track; see the module docstring). Nothing above this line changed.
# =============================================================================================================

STEP_M = 3.0                 # [invented] station step along the lap
EDGE_IN_M = 1.0              # [invented] outermost in-footprint sample this far inside the pavement edge: one 1 m
#                              3DEP cell, so no sample's cell reaches past the edge into the cut or the fill
OUTSIDE_M = (2.0, 5.0, 8.0)  # [invented] ground samples beyond each edge, for classification only
CUT_RISE_M = 1.0             # [invented] bench: the ground beside one edge rises >= this above the road centre ...
OTHER_RISE_M = 0.5           # [invented] ... while beside the other edge it rises < this (or falls)
CLASS_RUN_M = 30.0           # [invented] a classification run shorter than this joins its predecessor
STD_PCT = 2.0                # [std: docs/ROAD-CONSTRUCTION.md "Drainage": crown 2 %, or 2 % toward the cut ditch]
MAX_TILT_PCT = 6.0           # the legacy CAP above: rural superelevation maximum; a steeper reading is not a road
BANK_R_M = 100.0             # [invented] a curve tighter than this tilting INTO itself beyond STD_PCT is banking (A6)
MEAS_MEDIAN_M = 30.0         # [invented] along-lap median of the raw measurement
MEAS_MEAN_M = 15.0           # [invented] then a mean
RUNOFF_RATE = 0.12           # [invented] %/m: every transition ramps at most this fast (3.6 % per 30 m, under
#                              the gate's 4 %); a step of D becomes a ramp of D / 0.12 m (2 % -> 4 %: 33 m)
ROLL_WINDOW_M = 30.0         # [invented] the roll-rate gate (V3-PLAN P5): within any 30 m ...
ROLL_MAX_CHANGE_PCT = 4.0    # [invented] ... the tilt changes by <= 4 %
ROLL_SWING_PCT = 3.0         # [invented] ... and never swings from >= +3 % to <= -3 %


def roll_rate_check(st, tilt_pct, lap, *, closed=True, window_m=ROLL_WINDOW_M, max_change=ROLL_MAX_CHANGE_PCT,
                    swing=ROLL_SWING_PCT):
    """The roll-rate gate on one tilt series (stations ``st`` ascending, unique; wrapped by ``lap`` when closed).

    Returns {"change_fail": [i...], "swing_fail": [i...], "worst_change_pct", "worst_at_m", "swings": n}: a station
    is listed when some station within ``window_m`` AHEAD of it differs by more than ``max_change``, or (swing)
    when one is >= +swing and the other <= -swing. ``swings`` counts the separate runs of swing failures."""
    n = len(st)
    ch, sw = [], []
    worst, worst_at = 0.0, 0.0
    eps = 1e-9
    for i in range(n):
        j = i
        bad_c = bad_s = False
        while True:
            j2 = j + 1
            if j2 >= n:
                if not closed:
                    break
                j2 -= n
            if j2 == i:
                break
            d = st[j2] - st[i]
            if d < 0:
                d += lap
            if d > window_m + eps:
                break
            dt = abs(tilt_pct[j2] - tilt_pct[i])
            if dt > worst:
                worst, worst_at = dt, st[i]
            if dt > max_change + eps:
                bad_c = True
            if (tilt_pct[i] >= swing and tilt_pct[j2] <= -swing) or (tilt_pct[i] <= -swing and tilt_pct[j2] >= swing):
                bad_s = True
            j = j2
        if bad_c:
            ch.append(i)
        if bad_s:
            sw.append(i)
    runs = 0
    prev = None
    for i in sw:
        if prev is None or st[i] - st[prev] > window_m:
            runs += 1
        prev = i
    return {"change_fail": ch, "swing_fail": sw, "worst_change_pct": round(worst, 3), "worst_at_m": round(worst_at, 1),
            "swings": runs}


def _at(points_xz, st_v, s):
    import bisect
    lap = st_v[-1]
    s %= lap
    k = min(max(bisect.bisect_right(st_v, s), 1), len(st_v) - 1)
    t = (s - st_v[k - 1]) / max(1e-12, st_v[k] - st_v[k - 1])
    return (points_xz[k - 1][0] + t * (points_xz[k][0] - points_xz[k - 1][0]),
            points_xz[k - 1][1] + t * (points_xz[k][1] - points_xz[k - 1][1])), k - 1, t


def _heading(points_xz, st_v, s, half=3.0):
    a, _, _ = _at(points_xz, st_v, s - half)
    b, _, _ = _at(points_xz, st_v, s + half)
    return math.atan2(b[1] - a[1], b[0] - a[0])


def _signed_curvature(points_xz, st_v, s, half=10.0):
    """Turn over +-half divided by 2 half (1/m), + = turning left."""
    h0, h1 = _heading(points_xz, st_v, s - half), _heading(points_xz, st_v, s + half)
    d = (h1 - h0 + math.pi) % (2 * math.pi) - math.pi
    return d / (2 * half)


def plane_and_crown(offsets, z):
    """Least squares z = a + b*o - c*|o|: (b, c, a). b = plane tilt (+ = left up), c = crown (+ = centre high)."""
    n = len(offsets)
    zm = sum(z) / n
    om = sum(offsets) / n
    so = sum((o - om) ** 2 for o in offsets) or 1e-12
    b = sum((o - om) * (zz - zm) for o, zz in zip(offsets, z)) / so
    ab = [abs(o) for o in offsets]
    am = sum(ab) / n
    sa = sum((a2 - am) ** 2 for a2 in ab) or 1e-12
    c = -sum((a2 - am) * (zz - zm) for a2, zz in zip(ab, z)) / sa
    a = zm - b * om + c * am
    return b, c, a


def _classify(rise_left, rise_right):
    if rise_left >= CUT_RISE_M and rise_right < OTHER_RISE_M:
        return "bench_left"
    if rise_right >= CUT_RISE_M and rise_left < OTHER_RISE_M:
        return "bench_right"
    return "crown"


def _runs_join(cls, st, min_run):
    """Merge classification runs shorter than ``min_run`` metres into the run before them."""
    out = list(cls)
    n = len(out)
    step = (st[1] - st[0]) if n > 1 else 0.0
    for _ in range(3):
        runs = []
        i = 0
        while i < n:
            j = i
            while j + 1 < n and out[j + 1] == out[i]:
                j += 1
            runs.append((i, j))
            i = j + 1
        changed = False
        for r, (i, j) in enumerate(runs):
            if st[j] - st[i] + step < min_run and len(runs) > 1:
                src = out[runs[r - 1][0]] if r > 0 else out[runs[1][0]]
                for q in range(i, j + 1):
                    if out[q] != src:
                        out[q] = src
                        changed = True
        if not changed:
            break
    return out


def _cyc_mean(vals, st, lap, window_m):
    from scripts.elevation.road_profile import station_mean
    return station_mean(vals, st, lap, window_m, True)


def _cyc_median(vals, st, lap, window_m):
    from scripts.elevation.road_profile import station_median
    return station_median(vals, st, lap, window_m, True)


def _sample_cached(points, cache_p, sampler, log=print):
    import hashlib
    key = hashlib.sha256(json.dumps([[round(a, 7), round(b, 7)] for a, b in points]).encode()).hexdigest()[:16]
    if cache_p.exists():
        try:
            c = json.loads(cache_p.read_text(encoding="utf-8"))
            if c.get("fingerprint") == key and len(c.get("z", [])) == len(points):
                log(f"crossfall: 3DEP samples from cache {cache_p.name} ({len(points)} points)")
                return c["z"]
        except (ValueError, KeyError):
            pass
    log(f"crossfall: sampling {len(points)} points from USGS 3DEP ...")
    z = sampler(points)
    cache_p.write_text(json.dumps({"fingerprint": key, "source": "USGS 3DEP getSamples (scripts.elevation.usgs_3dep)",
                                   "z": [round(v, 3) for v in z]}), encoding="utf-8")
    return z


def runoff(vals, st, lap, rate_pct_per_m, closed=True):
    """The transitions: the mean of the greatest ``rate``-Lipschitz minorant and the least ``rate``-Lipschitz majorant
    of ``vals`` (each by forward / backward clamps by real station distance, wrapped twice on a closed lap). Where
    the series already changes no faster than ``rate`` it is returned unchanged; a step of D becomes a straight ramp
    of length D / rate centred on it. The result changes by at most ``rate`` per metre, so within any 30 m by at
    most 30 x rate."""
    n = len(vals)
    if n < 2:
        return list(vals)
    seg = [st[i + 1] - st[i] for i in range(n - 1)]
    seg_close = (lap - st[-1] + st[0]) if closed else 0.0

    def envelope(sign):
        v = [sign * x for x in vals]                 # minorant of v (sign=+1) / of -vals (sign=-1 -> majorant)
        for _ in range(2 if closed else 1):
            for i in range(1, n):
                v[i] = min(v[i], v[i - 1] + rate_pct_per_m * seg[i - 1])
            if closed:
                v[0] = min(v[0], v[-1] + rate_pct_per_m * seg_close)
            for i in range(n - 2, -1, -1):
                v[i] = min(v[i], v[i + 1] + rate_pct_per_m * seg[i])
            if closed:
                v[-1] = min(v[-1], v[0] + rate_pct_per_m * seg_close)
        return [sign * x for x in v]

    lo, hi = envelope(1.0), envelope(-1.0)
    return [(a + b) / 2.0 for a, b in zip(lo, hi)]


def banked_stations(tl, tr, curvature):
    """Stations on a curve tighter than BANK_R_M whose INSIDE half tilts down toward the curve's centre by more than
    the construction standard's 2 % (A6 / L10: the road is not banked; a bench sloping 2 % to a cut ditch on the
    inside of a bend is the standard, not banking)."""
    out = []
    for i, k in enumerate(curvature):
        if abs(k) < 1.0 / BANK_R_M:
            continue
        inside_down = -tl[i] if k > 0 else tr[i]       # left turn: the left half, + when its left edge is low
        if inside_down > STD_PCT + 1e-6:
            out.append(i)
    return out


def compose(st, lap, measured, classes, curvature, deck, *, closed=True):
    """The final per-half tilts (left_pct, right_pct, kinds, why, gate) from the smoothed measurement and the standard.

    A station keeps its measured tilt only when: it is not on a declared deck; the measurement is at least the
    standard's own 2 % (weaker is DEM noise against a crown), at most the 6 % cap, not banked into a curve
    (A6), the MEASURED series passes the roll-rate gate within +-ROLL_WINDOW_M of it (a failing stretch takes the
    standard: V3-PLAN P2 step 4), and it belongs to a kept run of at least CLASS_RUN_M. Every other station takes
    the construction standard. Each half is then given its transitions (``runoff`` at RUNOFF_RATE), so the result
    passes the roll-rate gate by construction; the gate is still run on it (and again by tools/verify_crossfall.py)."""
    n = len(st)
    std = []
    for c in classes:
        if c == "bench_left":
            std.append((-STD_PCT, -STD_PCT))
        elif c == "bench_right":
            std.append((STD_PCT, STD_PCT))
        else:
            std.append((-STD_PCT, STD_PCT))
    g_meas = roll_rate_check(st, measured, lap, closed=closed)
    bad_meas = set(g_meas["change_fail"]) | set(g_meas["swing_fail"])
    near_bad = [False] * n
    if bad_meas:
        for i in sorted(bad_meas):
            for j in range(n):
                d = abs(st[j] - st[i])
                if closed:
                    d = min(d, lap - d)
                if d <= ROLL_WINDOW_M:
                    near_bad[j] = True
    use, why = [], []
    for i in range(n):
        m = measured[i]
        into = -m if curvature[i] > 0 else m           # + = tilting INTO the curve (inside edge low)
        if deck[i]:
            use.append(False); why.append("deck")
        elif abs(m) < STD_PCT:
            use.append(False); why.append("below_standard")
        elif abs(m) > MAX_TILT_PCT:
            use.append(False); why.append("over_cap")
        elif abs(curvature[i]) >= 1.0 / BANK_R_M and into > STD_PCT:
            use.append(False); why.append("banked")
        elif near_bad[i]:
            use.append(False); why.append("roll_rate")
        else:
            use.append(True); why.append("measured")
    # a kept run shorter than CLASS_RUN_M is a blip, not a crossfall
    step = (st[1] - st[0]) if n > 1 else 0.0
    i = 0
    while i < n:
        if not use[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and use[j + 1]:
            j += 1
        if st[j] - st[i] + step < CLASS_RUN_M:
            for q in range(i, j + 1):
                use[q] = False
                why[q] = "short_run"
        i = j + 1
    # A6 after the runoff too: a ramp out of a kept measurement can carry it into a neighbouring tight curve. Any
    # station left banked into a curve sends the kept measurements within the ramp's reach to the standard.
    reach = (MAX_TILT_PCT + STD_PCT) / RUNOFF_RATE
    for _ in range(10):
        tl = runoff([measured[i] if use[i] else std[i][0] for i in range(n)], st, lap, RUNOFF_RATE, closed)
        tr = runoff([measured[i] if use[i] else std[i][1] for i in range(n)], st, lap, RUNOFF_RATE, closed)
        bank = banked_stations(tl, tr, curvature)
        flip = 0
        for i in bank:
            for j in range(n):
                d = abs(st[j] - st[i])
                if closed:
                    d = min(d, lap - d)
                if use[j] and d <= reach:
                    use[j] = False
                    why[j] = "banked_runoff"
                    flip += 1
        if not bank or not flip:
            break
    gl = roll_rate_check(st, tl, lap, closed=closed)
    gr = roll_rate_check(st, tr, lap, closed=closed)
    kinds = ["deck" if deck[i] else ("measured" if use[i] else classes[i]) for i in range(n)]
    return tl, tr, kinds, why, {"left": gl, "right": gr, "measured": g_meas}


def build_footprint(project_dir, *, sampler=None, log=print) -> dict:
    """Footprint-mode crossfall (see the module docstring). ``sampler(points_lonlat) -> [z]``: 3DEP by default."""
    from scripts.geometry.projection import _meters_per_degree
    project = Path(project_dir)
    data = project / "data"
    lc = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    pts = lc["points_xyz_m"]
    widths = lc["widths_m"]
    if lc.get("widths_frame") != "local":
        raise SystemExit("crossfall: centerline.local.json widths are not in the local frame (run "
                         "scripts.gps.measured_widths first: the footprint is the real width)")
    closed = abs(pts[0][0] - pts[-1][0]) < 1e-6 and abs(pts[0][2] - pts[-1][2]) < 1e-6
    if not closed:
        raise SystemExit("crossfall: footprint mode is written for a closed lap")
    xz = [(p[0], p[2]) for p in pts]
    st_v = [0.0]
    for i in range(1, len(xz)):
        st_v.append(st_v[-1] + math.hypot(xz[i][0] - xz[i - 1][0], xz[i][1] - xz[i - 1][1]))
    lap = st_v[-1]
    o = lc["origin"]
    mlon, mlat = _meters_per_degree(o["lat"])
    st = []
    s = 0.0
    while s < lap - 1e-6:
        st.append(s)
        s += STEP_M
    n = len(st)
    inside_off, sample_pts = [], []
    for s in st:
        p, k, t = _at(xz, st_v, s)
        w = widths[k] + t * (widths[k + 1] - widths[k])
        h = w / 2.0
        e = max(h - EDGE_IN_M, 0.5)
        offs_in = [e, e / 2.0, 0.0, -e / 2.0, -e]
        offs_out = [h + d for d in OUTSIDE_M] + [-(h + d) for d in OUTSIDE_M]
        hd = _heading(xz, st_v, s)
        nx, nz = -math.sin(hd), math.cos(hd)          # left normal (east, north)
        for off in offs_in + offs_out:
            x, z = p[0] + nx * off, p[1] + nz * off
            sample_pts.append((o["lon"] + x / mlon, o["lat"] + z / mlat))
        inside_off.append(offs_in)
    if sampler is None:
        from scripts.elevation.usgs_3dep import sample_points as sampler
    zs = _sample_cached(sample_pts, data / "crossfall.samples.json", sampler, log)
    nl = len(OUTSIDE_M)
    per = 5 + 2 * nl
    raw, crown_fit, classes, rise = [], [], [], []
    for i in range(n):
        zi = zs[i * per:(i + 1) * per]
        zin, zout = zi[:5], zi[5:]
        b, c, _a = plane_and_crown(inside_off[i], zin)
        raw.append(100.0 * b)
        crown_fit.append(100.0 * c)
        zc = zin[2]
        rl = sum(zout[:nl]) / nl - zc
        rr = sum(zout[nl:]) / nl - zc
        rise.append((round(rl, 2), round(rr, 2)))
        classes.append(_classify(rl, rr))
    classes = _runs_join(classes, st, CLASS_RUN_M)
    meas = _cyc_mean(_cyc_median(raw, st, lap, MEAS_MEDIAN_M), st, lap, MEAS_MEAN_M)
    curv = [_signed_curvature(xz, st_v, s) for s in st]
    decks = []
    bsp = data / "bridge.spans.json"
    if bsp.exists():
        decks = [tuple(d["local_m"]) for d in json.loads(bsp.read_text(encoding="utf-8")).get("declared") or []]
    deck = [any(a <= s <= b for a, b in decks) for s in st]
    g_raw = roll_rate_check(st, raw, lap)
    tl, tr, kinds, why, g_final = compose(st, lap, meas, classes, curv, deck)
    g_meas = g_final["measured"]
    plane = [(a2 + b2) / 2.0 for a2, b2 in zip(tl, tr)]
    crown = [(b2 - a2) / 2.0 for a2, b2 in zip(tl, tr)]
    passes = not (g_final["left"]["change_fail"] or g_final["left"]["swing_fail"]
                  or g_final["right"]["change_fail"] or g_final["right"]["swing_fail"])
    # banked into a curve: the inside half tilting down toward the curve centre by more than the standard's 2 %
    banked = len(banked_stations(tl, tr, curv))

    def frac(pred):
        return round(100.0 * sum(1 for i in range(n) if pred(i)) / n, 1)

    araw = sorted(abs(v) for v in raw)
    ameas = sorted(abs(v) for v in meas)
    summary = {
        "stations": n, "step_m": STEP_M, "lap_m": round(lap, 1),
        "kind_pct": {k2: frac(lambda i, k2=k2: kinds[i] == k2) for k2 in sorted(set(kinds))},
        "class_pct": {k2: frac(lambda i, k2=k2: classes[i] == k2) for k2 in sorted(set(classes))},
        "why_standard_pct": {k2: frac(lambda i, k2=k2: why[i] == k2) for k2 in sorted(set(why)) if k2 != "measured"},
        "raw": {"abs_p50_pct": round(araw[n // 2], 2), "abs_p95_pct": round(araw[19 * n // 20], 2),
                "at_or_over_6pct": frac(lambda i: abs(raw[i]) >= MAX_TILT_PCT),
                "roll_rate": {"change_fail": len(g_raw["change_fail"]), "swing_fail": len(g_raw["swing_fail"]),
                              "swings": g_raw["swings"]}},
        "measured_smoothed": {"abs_p50_pct": round(ameas[n // 2], 2), "abs_p95_pct": round(ameas[19 * n // 20], 2),
                              "max_abs_pct": round(ameas[-1], 2),
                              "roll_rate": {"change_fail": len(g_meas["change_fail"]),
                                            "swing_fail": len(g_meas["swing_fail"]), "swings": g_meas["swings"]}},
        "crown_fit_p50_pct": round(sorted(crown_fit)[n // 2], 2),
        "final": {"max_abs_plane_pct": round(max(abs(v) for v in plane), 2),
                  "max_abs_half_pct": round(max(max(abs(v) for v in tl), max(abs(v) for v in tr)), 2),
                  "roll_rate_pass": passes,
                  "worst_change_pct": max(g_final["left"]["worst_change_pct"], g_final["right"]["worst_change_pct"]),
                  "banked_into_curve_stations": banked},
    }
    out = {
        "status": "estimated",
        "_status_doc": "estimated until a 3DEP source-lidar sample agrees (REALISM section 5, V3-PLAN P2 step 4); "
                       "no lidar comparison has been made yet",
        "method": "footprint", "tool": "scripts/elevation/crossfall.py build_footprint",
        "frame": "local stations (centerline.local.json, v0 = route.start_at); + = left side higher",
        "params": {"STEP_M": STEP_M, "EDGE_IN_M": EDGE_IN_M, "OUTSIDE_M": list(OUTSIDE_M), "CUT_RISE_M": CUT_RISE_M,
                   "OTHER_RISE_M": OTHER_RISE_M, "CLASS_RUN_M": CLASS_RUN_M, "STD_PCT": STD_PCT,
                   "MAX_TILT_PCT": MAX_TILT_PCT, "BANK_R_M": BANK_R_M, "MEAS_MEDIAN_M": MEAS_MEDIAN_M,
                   "MEAS_MEAN_M": MEAS_MEAN_M, "RUNOFF_RATE": RUNOFF_RATE, "ROLL_WINDOW_M": ROLL_WINDOW_M,
                   "ROLL_MAX_CHANGE_PCT": ROLL_MAX_CHANGE_PCT, "ROLL_SWING_PCT": ROLL_SWING_PCT},
        "station_m": [round(s, 1) for s in st],
        "bank_rad": [round(math.atan(v / 100.0), 5) for v in plane],
        "crown_pct": [round(v, 3) for v in crown],
        "left_pct": [round(v, 3) for v in tl], "right_pct": [round(v, 3) for v in tr],
        "kind": kinds, "class": classes,
        "measured_pct": [round(v, 3) for v in meas], "raw_pct": [round(v, 3) for v in raw],
        "rise_beside_m": rise,
        "deadband": STD_PCT / 100.0, "cap": MAX_TILT_PCT / 100.0,
        "banked_pct": round(100.0 * sum(1 for k2 in kinds if k2 == "measured") / n, 1),
        "max_bank_pct": summary["final"]["max_abs_plane_pct"],
        "summary": summary,
    }
    (data / "crossfall.json").write_text(json.dumps(out), encoding="utf-8")
    log(f"crossfall (footprint): {n} stations every {STEP_M:g} m; kinds {summary['kind_pct']}; raw |tilt| p50 "
        f"{summary['raw']['abs_p50_pct']} % p95 {summary['raw']['abs_p95_pct']} % ({summary['raw']['at_or_over_6pct']} % "
        f">= 6 %), raw swings {g_raw['swings']}; final max plane {summary['final']['max_abs_plane_pct']} %, roll-rate "
        f"{'PASS' if passes else 'FAIL'} (worst {summary['final']['worst_change_pct']} % / 30 m)  [status: estimated]")
    return out


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    proj = Path(args[0] if args else ".")
    cfgp = proj / "track.config.json"
    cf = {}
    if cfgp.exists():
        cf = (json.loads(cfgp.read_text(encoding="utf-8")).get("road_profile") or {}).get("crossfall") or {}
    if isinstance(cf, dict) and cf.get("method") == "footprint":
        build_footprint(proj)
    else:
        build(proj)
    return 0


if __name__ == "__main__":
    sys.exit(main())

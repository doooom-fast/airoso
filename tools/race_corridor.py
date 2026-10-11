"""The race corridors' closure line — PURE (no bpy), ledger 0049 (Kevin 2026-10-11).

Kevin: "racetrack versions of these, we need full intersections available for turning. And the entire
other lane blocked off from access." / "We want more or less an Alvarado's width for the entire track with
deviances in various areas."

Each race layout drives a lane bounded on its race side by the existing curb strip (its right-hand curb,
the whole lap) and on the far side by a CLOSURE: the same jersey strip standing so that the lane is
Alvarado's width as raced — 11.36 m face to face (13.00 m curb to curb minus the two 0.82 m strip insets;
MEASURED, tools/barrier_bands.py re-measures it). This module derives that closure line per direction; the
band writer validates it, writes it into data/barrier_bands.json (version 2) and the author sweeps it.

Port of the read-only design study's solver (scratchpad corridor/work/corridor.py, 2026-10-11; its output is
pinned as tests/tools/fixtures/sd_corridor_proto.json) with the study's hard-coded SD tables replaced by
the declaration (track.config.json race.corridor) and the data:

  frames   v = centreline vertex; y = metres forward-LEFT of the increasing-v tangent; g = metres toward
           THIS direction's race side (race_cw: g = -y, race_acw: g = +y).
  base     B = min(w, gauss_sigma(open_+-base_open_m(w))): every curb flare or notch shorter than
           2 x base_open_m disappears, so the closure stays straight while the race-side strip follows the
           real curb (a flare widens the lane behind the moving strip instead).
  target   g_t = B/2 - inset - half - clear_width; beside an island max(g_t, F + strip centre) with F the
           island race face (data width) closed over +-island_env_m; across a short gap between two
           islands (an `opening`, Del Cerro) F is interpolated nose to nose.
  bounds   L = max(far strip centre, AUTHORED island half + strip centre) (the 0.25 m nose taper included:
           the closure passes every nose on the race side); U = B/2 - inset - half - clear_floor; at the
           two pins L = U = the far strip centre.
  rates    slope-limited envelopes: toward the race side <= 1:rate_toward, away <= 1:rate_away; within
           pin_zone_m of a pin the gentlest feasible rate >= 1:pin_rate_min (pin_rate overrides per pin
           vertex — the I-8 deck end is taken at speed, 1:10).
  solve    min sum (dg)^2/ds + sum ds (g - g_t)^2 / attract^2 within [L, U] — projected SOR (omega 1.8,
           1e-6), then a smooth_sigma_m Gaussian (+-4 vertices), re-clamped, re-pinned.

Everything here is a function of (points, widths, island widths, the declared zones, the parameters); no
file is read. The study's constants that are now parameters carry their study values as defaults
(fleet/GATES-CHANGELOG.md marks each INVENTED or MEASURED).
"""
from __future__ import annotations

import math

INSET_M = 0.82            # strip road face from the curb line (race.edge_inset_m) — MEASURED declaration
BARRIER_HALF_M = 0.335    # concrete_barrier_4m.obj half base — MEASURED asset
NOSE_HALF, NOSE_VERTS, ISLAND_MIN_VERTS = 0.25, 3, 6   # tools/author_median_blend.py (MEASURED)

DEFAULTS = {
    "clear_width_m": 11.36,      # MEASURED: Alvarado as raced, face to face
    "clear_floor_m": 10.86,      # INVENTED: band -0.5
    "clear_hard_min_m": 6.5,     # INVENTED
    "pocket_min_m": 2.0,         # INVENTED
    "rate_toward_race_side": 12.0,   # INVENTED: 1:12
    "rate_away": 6.0,                # INVENTED: 1:6
    "pin_zone_m": 120.0,             # INVENTED
    "pin_rate_min": 6.0,             # INVENTED: 1:6 or gentler within a pin zone where feasible
    "pin_rate": {},                  # {"<vertex>": run per lateral} — e.g. {"4454": 10}
    "steepest_pin_rate": 3.0,        # INVENTED: anything steeper than 1:3 fails
    "base_open_m": 60.0,             # INVENTED
    "base_sigma_m": 20.0,            # INVENTED
    "island_env_m": 30.0,            # INVENTED
    "attract_m": 40.0,               # INVENTED
    "smooth_sigma_m": 4.0,           # INVENTED
    "opening_max_m": 100.0,          # INVENTED: two islands closer than this are one closure line, nose to nose
    "sor_omega": 1.8,
    "sor_tol_m": 1e-6,
    "sor_max_sweeps": 6000,
}


def params_from(cfg_corridor: dict | None) -> dict:
    p = dict(DEFAULTS)
    for k, v in (cfg_corridor or {}).items():
        if k in DEFAULTS:
            p[k] = v
    p["pin_rate"] = {int(k): float(v) for k, v in (p.get("pin_rate") or {}).items()}
    return p


def ring_count(pts) -> int:
    n = len(pts)
    if n > 1 and abs(pts[0][0] - pts[-1][0]) < 1e-6 and abs(pts[0][2] - pts[-1][2]) < 1e-6:
        return n - 1
    return n


def stations(pts):
    st = [0.0]
    for i in range(1, len(pts)):
        st.append(st[-1] + math.hypot(pts[i][0] - pts[i - 1][0], pts[i][2] - pts[i - 1][2]))
    return st


def in_rng(v: int, a: int, b: int, n: int) -> bool:
    """v inside the inclusive ring interval a..b (wrapping when b < a)"""
    v %= n
    a %= n
    b %= n
    return a <= v <= b if a <= b else (v >= a or v <= b)


def walk(i: int, j: int, n: int):
    if j >= i:
        return list(range(i, j + 1))
    return list(range(i, n)) + list(range(0, j + 1))


def _win(st, n, i, half):
    """the vertex window i-..i+ within `half` metres along (no wrap — the study's rule)"""
    lo = hi = i
    while lo > 0 and st[i] - st[lo - 1] <= half:
        lo -= 1
    while hi < n - 1 and st[hi + 1] - st[i] <= half:
        hi += 1
    return lo, hi


def _gauss(st, n, vals, sig):
    out = list(vals)
    for i in range(n):
        lo, hi = _win(st, n, i, 3 * sig)
        sw = sv = 0.0
        for k in range(lo, hi + 1):
            w = math.exp(-0.5 * ((st[k] - st[i]) / sig) ** 2)
            sw += w
            sv += w * vals[k]
        out[i] = sv / sw
    return out


def base_width(st, widths, n, open_m, sigma_m):
    """the flare-free base width: widths opened (erosion then dilation) over +-open_m, Gaussian sigma_m,
    never wider than the real road"""
    win = [_win(st, n, i, open_m) for i in range(n)]
    ero = [min(widths[win[i][0]:win[i][1] + 1]) for i in range(n)]
    opn = [max(ero[win[i][0]:win[i][1] + 1]) for i in range(n)]
    wb = _gauss(st, n, opn, sigma_m)
    return [min(wb[i], widths[i]) for i in range(n)]


def island_runs(island_w, n, min_verts=ISLAND_MIN_VERTS):
    """[(a, b)] inclusive runs of island_w > 0 that tools/author_median_blend.py authors (>= 6 vertices)"""
    out, i = [], 0
    while i < n:
        if island_w[i] <= 0:
            i += 1
            continue
        j = i
        while j < n and island_w[j] > 0:
            j += 1
        if j - i >= min_verts:
            out.append((i, j - 1))
        i = j
    return out


def authored_half(island_w, n):
    """the AUTHORED island half-width per vertex: runs of >= 6 vertices, the 0.25 m nose taper over 3 stations"""
    half = [0.0] * n
    for a, b in island_runs(island_w, n):
        L = b - a + 1
        for si, k in enumerate(range(a, b + 1)):
            h = island_w[k] / 2.0
            if si < NOSE_VERTS:
                h = NOSE_HALF + (h - NOSE_HALF) * si / NOSE_VERTS
            if (L - 1 - si) < NOSE_VERTS:
                h = NOSE_HALF + (h - NOSE_HALF) * (L - 1 - si) / NOSE_VERTS
            half[k] = h
    return half


def island_zones(island_w, st, n, opening_max_m):
    """island runs merged across short gaps: ([(a, b)] zones, [(a, b)] openings) — an opening is the gap
    between two islands closer than opening_max_m (a real 4-way like Del Cerro: closed nose to nose)"""
    runs = island_runs(island_w, n)
    zones, openings = [], []
    for a, b in runs:
        if zones and st[a] - st[zones[-1][1]] <= opening_max_m:
            openings.append((zones[-1][1] + 1, a - 1))
            zones[-1] = (zones[-1][0], b)
        else:
            zones.append((a, b))
    return zones, openings


def island_face_env(st, n, island_w, zones, openings, env_m):
    """the island race face per vertex (data half-width) closed over +-env_m inside each zone, interpolated
    linearly across an opening from nose to nose (the study's rule)"""
    face = [0.0] * n
    for a, b in zones:
        for i in range(a, b + 1):
            lo, hi = _win(st, n, i, env_m)
            lo, hi = max(lo, a), min(hi, b)
            face[i] = max(island_w[lo:hi + 1]) / 2.0
        tmp = face[:]
        for i in range(a, b + 1):
            lo, hi = _win(st, n, i, env_m)
            lo, hi = max(lo, a), min(hi, b)
            tmp[i] = min(face[lo:hi + 1])
        for i in range(a, b + 1):
            face[i] = tmp[i]
    for a, b in openings:
        fa, fb = face[a - 1], face[b + 1]
        for i in range(a, b + 1):
            t = (st[i] - st[a - 1]) / (st[b + 1] - st[a - 1])
            face[i] = fa + (fb - fa) * t
    return face


def solve(pts, widths, island_w, free_fn, direction, params, *, inset=INSET_M, half=BARRIER_HALF_M, start=None,
          context=None):
    """The closure line of ONE direction ('cw' = increasing vertex, 'acw' = decreasing).

    free_fn(v) -> True where no closure stands (whole street and the open boxes). Returns
    {e, order, g (per vertex: lateral toward the race side, None where no closure), runs: [run record]};
    each run record carries its vertices in travel order (`vs`, pins first and last), arc metres `rr`, the
    solved `g`, target `t`, bounds `L` / `Lraw` / `U`, `isl` (authored island bound or None), `face`
    (enveloped island face or None), pin rates `k_pin` (lateral per metre), per-step limits `kc` / `kd`,
    the pin-zone flags and `infeas` (vertices where the hard bounds cross)."""
    p = params
    n = ring_count(pts)
    ctx = context or prepare(pts, widths, island_w, p)
    st, WB, HALF_AUTH, FACE_ENV = ctx["st"], ctx["WB"], ctx["half_auth"], ctx["face_env"]
    W = widths
    strip_c = inset - half                  # 0.485: the strip centre from the curb line
    w_t, w_lo = float(p["clear_width_m"]), float(p["clear_floor_m"])
    k_conv, k_div = 1.0 / float(p["rate_toward_race_side"]), 1.0 / float(p["rate_away"])
    k_pin_min = 1.0 / float(p["pin_rate_min"])
    zone_m = float(p["pin_zone_m"])
    pin_k = {int(v): 1.0 / float(r) for v, r in (p.get("pin_rate") or {}).items()}
    mu = 1.0 / float(p["attract_m"]) ** 2
    e = -1 if direction == "cw" else +1
    order = list(range(n)) if direction == "cw" else [(-k) % n for k in range(n)]
    if start is None:
        start = next((v for v in range(n) if free_fn(v)), 0)
    k0 = order.index(start)
    order = order[k0:] + order[:k0]
    r = [0.0] * n
    for k in range(1, n):
        a, b = order[k - 1], order[k]
        r[k] = r[k - 1] + math.hypot(pts[b][0] - pts[a][0], pts[b][2] - pts[a][2])
    runs = []
    k = 0
    while k < n:
        if free_fn(order[k]):
            k += 1
            continue
        k1 = k
        while k1 + 1 < n and not free_fn(order[k1 + 1]):
            k1 += 1
        runs.append((k - 1, min(k1 + 1, n - 1)))
        k = k1 + 1
    out = {"e": e, "order": order, "g": [None] * n, "runs": []}
    NEG, POS = -1e9, 1e9
    for (ka, kb) in runs:
        ks = list(range(ka, kb + 1))
        vs = [order[q] for q in ks]
        m = len(ks)
        rr = [r[q] - r[ka] for q in ks]
        g_far = [-(W[v] / 2.0 - strip_c) for v in vs]
        g_rsf_base = [WB[v] / 2.0 - inset for v in vs]
        isl = [HALF_AUTH[v] + strip_c if HALF_AUTH[v] > 0 else None for v in vs]
        face_env = [FACE_ENV[v] + strip_c if FACE_ENV[v] > 0 else None for v in vs]
        t = []
        for j in range(m):
            tp = g_rsf_base[j] - half - w_t
            t.append(max(tp, face_env[j]) if face_env[j] is not None else tp)
        pin0, pin1 = g_far[0], g_far[-1]
        d0 = rr
        d1 = [rr[-1] - x for x in rr]

        def need(pin_val, dist):
            req = 0.0
            for j in range(m):
                if dist[j] <= zone_m and isl[j] is not None and dist[j] > 1e-6:
                    req = max(req, (isl[j] - pin_val) / dist[j])
            return req
        k_pin0 = max(pin_k.get(vs[0], k_pin_min), need(pin0, d0) * 1.02)
        k_pin1 = max(pin_k.get(vs[-1], k_pin_min), need(pin1, d1) * 1.02)
        kc = [k_conv] * m
        kd = [k_div] * m
        zone0 = [False] * m
        zone1 = [False] * m
        for j in range(m):
            if d0[j] <= zone_m:
                kc[j] = max(kc[j], k_pin0)
                kd[j] = max(kd[j], k_pin0)
                zone0[j] = True
            if d1[j] <= zone_m:
                kc[j] = max(kc[j], k_pin1)
                kd[j] = max(kd[j], k_pin1)
                zone1[j] = True
        L = [max(g_far[j], isl[j] if isl[j] is not None else NEG) for j in range(m)]
        L[0], L[-1] = pin0, pin1
        Lraw = L[:]
        for j in range(m - 2, -1, -1):
            L[j] = max(L[j], L[j + 1] - kc[j] * (rr[j + 1] - rr[j]))
        for j in range(1, m):
            L[j] = max(L[j], L[j - 1] - kd[j] * (rr[j] - rr[j - 1]))
        Uh = [POS] * m
        Uh[0], Uh[-1] = pin0, pin1
        for j in range(1, m):
            Uh[j] = min(Uh[j], Uh[j - 1] + kc[j] * (rr[j] - rr[j - 1]))
        for j in range(m - 2, -1, -1):
            Uh[j] = min(Uh[j], Uh[j + 1] + kd[j] * (rr[j + 1] - rr[j]))
        U = [g_rsf_base[j] - half - w_lo for j in range(m)]
        U[0], U[-1] = pin0, pin1
        for j in range(m - 2, -1, -1):
            U[j] = min(U[j], U[j + 1] + kd[j] * (rr[j + 1] - rr[j]))
        for j in range(1, m):
            U[j] = min(U[j], U[j - 1] + kc[j] * (rr[j] - rr[j - 1]))
        U = [min(U[j], Uh[j]) for j in range(m)]
        infeas = [vs[j] for j in range(m) if L[j] > Uh[j] + 1e-6]
        U = [max(U[j], L[j]) for j in range(m)]
        g = [min(max(t[j], L[j]), U[j]) for j in range(m)]
        g[0], g[-1] = pin0, pin1
        omega, tol = float(p["sor_omega"]), float(p["sor_tol_m"])
        it = 0
        for it in range(int(p["sor_max_sweeps"])):
            mx = 0.0
            for j in range(1, m - 1):
                a = rr[j] - rr[j - 1] or 1e-3
                b = rr[j + 1] - rr[j] or 1e-3
                h = 0.5 * (a + b)
                new = (g[j - 1] / a + g[j + 1] / b + mu * h * t[j]) / (1 / a + 1 / b + mu * h)
                new = g[j] + omega * (new - g[j])
                new = min(max(new, L[j]), U[j])
                mx = max(mx, abs(new - g[j]))
                g[j] = new
            if mx < tol:
                break
        sig = float(p["smooth_sigma_m"])
        sm = g[:]
        for j in range(1, m - 1):
            sw = sv = 0.0
            for q in range(max(0, j - 4), min(m, j + 5)):
                w = math.exp(-0.5 * ((rr[q] - rr[j]) / sig) ** 2)
                sw += w
                sv += w * g[q]
            sm[j] = min(max(sv / sw, L[j]), U[j])
        g = sm
        g[0], g[-1] = pin0, pin1
        for j, v in enumerate(vs):
            out["g"][v] = g[j]
        out["runs"].append({"vs": vs, "rr": rr, "g": g, "t": t, "L": L, "Lraw": Lraw, "U": U, "isl": isl,
                            "face": face_env, "g_far": g_far, "k_pin": (k_pin0, k_pin1), "kc": kc, "kd": kd,
                            "zone0": zone0, "zone1": zone1, "infeas": infeas, "iters": it})
    return out


def prepare(pts, widths, island_w, params):
    """the per-track arrays both directions share: stations, base width, authored island half, the enveloped
    island face, the island zones and openings"""
    n = ring_count(pts)
    st = stations(pts)
    W = [float(w) for w in widths]
    iw = [float(x) for x in island_w[:n]] + [0.0] * max(0, n - len(island_w))
    WB = base_width(st, W, n, float(params["base_open_m"]), float(params["base_sigma_m"]))
    zones, openings = island_zones(iw, st, n, float(params["opening_max_m"]))
    face = island_face_env(st, n, iw, zones, openings, float(params["island_env_m"]))
    return {"n": n, "st": st, "WB": WB, "half_auth": authored_half(iw, n), "face_env": face,
            "island_zones": zones, "openings": openings}


def lane_by_vertex(y_closure, widths, n, direction, *, inset=INSET_M, half=BARRIER_HALF_M, pins=()):
    """[y_lo, y_hi] per vertex (forward frame, the corridor FACES): race_cw [-(w/2 - inset), y - half],
    race_acw [y + half, w/2 - inset]; full width (both curb strip faces) where no closure stands and at the
    pins (the closure end is buried in the far strip)."""
    pins = set(pins)
    out = []
    for v in range(n):
        face = widths[v] / 2.0 - inset
        y = y_closure[v]
        if y is None or v in pins:
            out.append([-face, face])
        elif direction == "cw":
            out.append([-face, y - half])
        else:
            out.append([y + half, face])
    return out


RADIUS_STENCIL_M = 6.0    # the study's stencil: the circle through the points >= 6 m before and after a vertex


def plan_radius(pts, n, vs, y, stencil_m=RADIUS_STENCIL_M):
    """(min plan radius (m) of the closure centre polyline, its vertex, backward steps) along the run `vs` in its
    TRAVEL order. Radius: the circle through the points >= stencil_m before / after each interior vertex (the
    study's +-6 m stencil; a 3-point circle on 3 m spacing reads raster-level jitter as a 10 m bend). Backward
    step: a step that does not advance along the centreline's own direction of travel there (a fold)."""
    def at(v, yy):
        a, b = pts[(v - 1) % n], pts[(v + 1) % n]
        tx, tz = b[0] - a[0], b[2] - a[2]
        L = math.hypot(tx, tz) or 1.0
        return pts[v][0] - tz / L * yy, pts[v][2] + tx / L * yy
    q = [at(v, y[v]) for v in vs]
    back = 0
    for i in range(1, len(q)):
        a, b = pts[vs[i - 1]], pts[vs[i]]
        tx, tz = b[0] - a[0], b[2] - a[2]                  # travel direction of the centreline itself
        if (q[i][0] - q[i - 1][0]) * tx + (q[i][1] - q[i - 1][1]) * tz <= 0.0:
            back += 1
    arc = [0.0]
    for i in range(1, len(vs)):
        a, b = pts[vs[i - 1]], pts[vs[i]]
        arc.append(arc[-1] + math.hypot(b[0] - a[0], b[2] - a[2]))
    best, bv = float("inf"), None
    for i in range(1, len(q) - 1):
        ia, ib = i, i
        while ia > 0 and arc[i] - arc[ia] < stencil_m:
            ia -= 1
        while ib < len(q) - 1 and arc[ib] - arc[i] < stencil_m:
            ib += 1
        if not ia < i < ib:
            continue
        (ax, az), (bx, bz), (cx, cz) = q[ia], q[i], q[ib]
        ab, bc, ca = math.hypot(bx - ax, bz - az), math.hypot(cx - bx, cz - bz), math.hypot(ax - cx, az - cz)
        cross = abs((bx - ax) * (cz - az) - (bz - az) * (cx - ax))
        if cross < 1e-9:
            continue
        R = ab * bc * ca / (2.0 * cross)
        if R < best:
            best, bv = R, vs[i]
    return best, bv, back

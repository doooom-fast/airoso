"""A divided road at its real width off the lidar's measured faces (ledger 0098 0.2.13, Sand Creek's North Colorado Blvd;
the records it writes are opt-in: lm_intake.carriageway, lm_intake.side_pieces, route.islands).

The Mac's decisions, 2026-11-24 / 25 (relayed, Kevin's "I just want real", "Full street width"):
  * the lap is the NEAR carriageway: its right edge on the measured right curb over s 66-348, its left edge on the
    median's near face over s 143-348 (the divided stretch), each eased in and out over about 25 m (a raised cosine)
    outside both pads' cut rows; everywhere else the lap is as built;
  * the median is a concrete island beside it, top on the measured faces, only where the lidar reads a raised median;
  * the far carriageway is its own side piece (grid_primary_colorado_sb, so tools/trim_connectors.py hosts the street that
    meets it), between the median's far face and the far curb, its ends open.

Evidence: the G10's stations (tracks/<port>/source/roads_lidar_g10/lap_colorado_quebec.lidar.json, roads_lidar_g10.py:
USGS CO_DRCOG_2_2020 class 2, every 2.5 m of the lap's s, faces good to about 0.25 m). Their s and u are on the line the
assembler BUILDS (a draft's data/centerline.local.json: the intake's line through scripts-v021 geometry/smooth.py; matched
to 0.1 mm), u + = left of travel. Per face key the stations' readings (a face of kind "none" is no reading) become a
series along s: the median of the readings within +-MED_HALF_M, rows with fewer than MIN_READ readings filled linearly
from the measured rows within GAP_M, then a Gaussian of SMOOTH_M. Inside a span the edge IS that series; outside it the
CHANGE from today's edge fades to nothing over TAPER_M (raised cosine), holding the span end's target.

The lap (record source/carriageway_*.json, applied by tools/lm_engine_intake.py apply_carriageway): per vertex of the
INTAKE's line (a draft's data/centerline.raw.local.json, the line the record is applied to) the width = left - right and
the line moved (left + right) / 2 along the built line's left normal, the move pre-compensated for the assembler's
smoothing (D -> 2 D - S(D), as tools/edge_retrace.py shift_precomp), so the BUILT edges land on the targets; the residual
(built edge - target, after the assembler's own smoothing) is reported per side. Every row names its vertex, its
position and its width before: the intake refuses the record on any other line.

The far carriageway (source/side_pieces_*.json, {"connectors": [...]}, lm_intake.side_pieces): one connector per span,
a point per station, centre (far face + far curb) / 2, width far curb - far face, height the mean of the two faces'
pavement-side heights (the lidar's road, not the 3DEP); open_ends true (tools/trim_connectors.py never stretches its ends
onto the lap, which lies within its REACH_M of both).

The median island (route.islands entries, written beside the records as islands_*.json for the config): rows [xa, za, xb,
zb] per station where BOTH median faces read a raised median (a run broken by more than one station is a gap: no raised
median, no island), edge A ISLAND_ON_ROAD_M onto the lap's pavement and edge B as far onto the far piece's (the islands
author reads the ROAD under each edge; the curb face is the reading's), rise_m [a, b] the faces' measured steps (medians
over the island's rows).

Pure Python (stdlib); tests/tools/test_divided_road.py.

    python tools/divided_road.py <port track dir> --draft <a draft project dir> [--write]
"""
from __future__ import annotations

import bisect
import json
import math
import sys
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]
if str(AIROSO) not in sys.path:
    sys.path.insert(0, str(AIROSO))

MED_HALF_M = 7.5        # tools/edge_retrace.py MED_HALF_M: a row's reading = the median of the readings within +-7.5 m
MIN_READ = 2            # [invented] readings inside a row's window before it measures (stations are 2.5 m apart: 6 in 15 m)
GAP_M = 40.0            # tools/edge_retrace.py GAP_M: a row with no reading takes the line between measured rows <= 40 m
SMOOTH_M = 4.0          # [invented] the series' Gaussian (the faces are quantised to 0.25 m; the assembler smooths ~6 m)
TAPER_M = 25.0          # the Mac 2026-11-25: "raised-cosine eases of about 25 m"
ISLAND_ON_ROAD_M = 0.25  # [invented] each island edge this far onto its pavement: the islands author must find ROAD under it
ISLAND_GAP_STATIONS = 1  # [invented] a run of the raised median survives one unread station; two or more = a gap
ISLAND_MIN_M = 10.0     # [invented] a run shorter than this is no island (a lone reading)

FACE_KEYS = ("right_edge", "median_near", "median_far", "left_edge")
# the pavement side of each face (+1: the road lies at larger u; -1: at smaller u)
ROAD_SIDE = {"right_edge": +1, "median_near": -1, "median_far": +1, "left_edge": -1}


def _gauss(xs, ys, sigma):
    out = []
    for i, x in enumerate(xs):
        num = den = 0.0
        lo = bisect.bisect_left(xs, x - 3 * sigma)
        hi = bisect.bisect_right(xs, x + 3 * sigma)
        for j in range(lo, hi):
            w = math.exp(-0.5 * ((xs[j] - x) / sigma) ** 2)
            num += w * ys[j]
            den += w
        out.append(num / den)
    return out


def face_reading(st, key, kinds=("curb",), divided_only=False):
    """(u, pavement-side height, step) of one station's face, or None: no face, a kind not in ``kinds`` (the G10's
    "fall" / "drop" / "none" are the pavement falling away or no step: not the curb the decisions name), or, with
    divided_only, a station the G10 did not read as divided (on an undivided station its left_edge can be the median's
    near face: s 170.8, 265.8, 310-325)"""
    f = (st.get("faces") or {}).get(key)
    if not f or f.get("kind") not in kinds or f.get("u_m") is None:
        return None
    if divided_only and not st.get("divided"):
        return None
    side = ROAD_SIDE[key]
    y_road = f.get("y_plus_side") if side > 0 else f.get("y_minus_side")
    y_other = f.get("y_minus_side") if side > 0 else f.get("y_plus_side")
    step = None if (y_road is None or y_other is None) else float(y_other) - float(y_road)
    return float(f["u_m"]), (None if y_road is None else float(y_road)), step


def series(stations, key, what=0, divided_only=False):
    """the face's measured series along the stations' s: {s: value} over every station from the first to the last
    measured row (what 0 = u, 1 = pavement height); rows past GAP_M of any measured row are left out"""
    s_all = [float(st["s_lap"]) for st in stations]
    raw = []
    for st in stations:
        r = face_reading(st, key, divided_only=divided_only)
        raw.append(None if r is None or r[what] is None else r[what])
    meas_s, meas_v = [], []
    for i, s in enumerate(s_all):
        win = [raw[j] for j in range(len(s_all)) if raw[j] is not None and abs(s_all[j] - s) <= MED_HALF_M + 1e-6]
        if raw[i] is not None and len(win) >= MIN_READ:
            win.sort()
            m = len(win)
            meas_s.append(s)
            meas_v.append(win[m // 2] if m % 2 else 0.5 * (win[m // 2 - 1] + win[m // 2]))
    if not meas_s:
        return {}
    filled_s, filled_v = [], []
    for s in s_all:
        if s < meas_s[0] or s > meas_s[-1]:
            continue
        j = bisect.bisect_left(meas_s, s)
        if j < len(meas_s) and abs(meas_s[j] - s) < 1e-6:
            v = meas_v[j]
        else:
            a, b = meas_s[j - 1], meas_s[j]
            if b - a > 2 * GAP_M:
                continue
            t = (s - a) / (b - a)
            v = meas_v[j - 1] + (meas_v[j] - meas_v[j - 1]) * t
        filled_s.append(s)
        filled_v.append(v)
    sm = _gauss(filled_s, filled_v, SMOOTH_M)
    return dict(zip(filled_s, sm))


def at(ser: dict, s: float, hold=True):
    """the series at s (linear between its rows); outside it the nearest end's value (hold) or None"""
    ks = sorted(ser)
    if not ks:
        return None
    if s <= ks[0]:
        return ser[ks[0]] if hold else None
    if s >= ks[-1]:
        return ser[ks[-1]] if hold else None
    j = bisect.bisect_right(ks, s)
    a, b = ks[j - 1], ks[j]
    t = (s - a) / (b - a)
    return ser[a] + (ser[b] - ser[a]) * t


def weight(s, span, taper=TAPER_M):
    """1 inside span [a, b], a raised cosine to 0 over taper outside it (stations on an open stretch)"""
    a, b = span
    d = a - s if s < a else (s - b if s > b else 0.0)
    if d <= 0:
        return 1.0
    return 0.5 + 0.5 * math.cos(math.pi * d / taper) if d < taper else 0.0


def unwrapped(stations, lap_m):
    """the stations with s_lap made monotonic along the stretch: a stretch over the closed lap's v0 (Colorado: v3205 ->
    v140) has its first stations near the lap's end; those read s - lap_m (negative), so one span reads one way"""
    s0 = float(stations[0]["s_lap"])
    base = s0 if s0 < lap_m / 2.0 else s0 - lap_m
    out = []
    for st_ in stations:
        c = dict(st_)
        c["s_lap"] = round(base + ((float(st_["s_lap"]) - s0) % lap_m), 3)
        out.append(c)
    return out


def _smooth_mod():
    import importlib.util
    sp = importlib.util.spec_from_file_location(
        "_lm_smooth_dr", AIROSO / "tracks" / "san-diego-lake-murray" / "scripts-v021" / "geometry" / "smooth.py")
    mod = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(mod)
    return mod


def _stations(P):
    st = [0.0]
    for a, b in zip(P, P[1:]):
        st.append(st[-1] + math.hypot(b[0] - a[0], b[2] - a[2]))
    return st


def _left_normals(P):
    n = len(P)
    out = []
    for k in range(n):
        a, b = P[max(k - 1, 0)], P[min(k + 1, n - 1)]
        tx, tz = b[0] - a[0], b[2] - a[2]
        L = math.hypot(tx, tz) or 1.0
        out.append((-tz / L, tx / L))
    return out


def carriageway(raw_pts, widths, closed, stations, spec, route):
    """the lap's rows (module doc). raw_pts / widths: the intake's line; stations: the G10's; spec: {"right": {"span":
    [s0, s1]}, "left": {...}, "taper_m"}; route: the port's route (smooth_* for the assembler's smoothing)."""
    sm = _smooth_mod()
    kw = dict(sigma_pts=float(route.get("smooth_sigma_pts", 2.0)), passes=int(route.get("smooth_passes", 2)),
              sigma_y_pts=0.0)
    P = [tuple(float(c) for c in p) for p in raw_pts]
    S = sm.smooth_centerline(P, **kw)
    st = _stations(S)
    taper = float(spec.get("taper_m", TAPER_M))
    ser = {"right": series(stations, "right_edge"), "left": series(stations, "median_near")}
    s_lo = min(float(spec[sd]["span"][0]) for sd in ("right", "left")) - taper
    s_hi = max(float(spec[sd]["span"][1]) for sd in ("right", "left")) + taper
    lap = st[-1]
    rows_k = [k for k in range(len(P) - (1 if closed else 0)) if s_lo <= st[k] <= s_hi]
    target = {}
    for sd, sign in (("right", -1), ("left", +1)):
        span = [float(v) for v in spec[sd]["span"]]
        for k in rows_k:
            w_ = weight(st[k], span, taper)
            if w_ <= 0.0:
                continue
            u_t = at(ser[sd], min(max(st[k], span[0]), span[1]))
            if u_t is None:
                raise SystemExit(f"[divided_road] {sd}: no measured face in span {span}")
            today = sign * widths[k] / 2.0
            target.setdefault(k, {})[sd] = (today + w_ * (u_t - today), u_t, w_)
    # the change per vertex: shift D (+ = left) about the BUILT line and the new width
    D = [0.0] * len(P)
    W = list(widths)
    rows = []
    for k in sorted(target):
        r_ = target[k].get("right", (-widths[k] / 2.0, None, 0.0))[0]
        l_ = target[k].get("left", (widths[k] / 2.0, None, 0.0))[0]
        D[k] = (l_ + r_) / 2.0
        W[k] = round(l_ - r_, 3)
    NS = _left_normals(S)
    moved = [(p[0] + NS[k][0] * D[k], p[1], p[2] + NS[k][1] * D[k]) for k, p in enumerate(P)]
    if closed:
        moved[-1] = moved[0]
    # the assembler smooths P + D into S(P) + S(D): 2 D - S(D) in its place builds ~D (edge_retrace shift_precomp)
    s_moved = sm.smooth_centerline(moved, **kw)
    region = set(rows_k)
    pre = [(q[0] + (q[0] - p[0]) - (sq[0] - sp[0]), q[1], q[2] + (q[2] - p[2]) - (sq[2] - sp[2])) if k in region else p
           for k, (p, q, sp, sq) in enumerate(zip(P, moved, S, s_moved))]   # nothing moves outside the eases
    if closed:
        pre[-1] = pre[0]
    # the check: what the assembler builds from the record, against the targets
    B = sm.smooth_centerline(pre, **kw)
    NB = _left_normals(B)
    res = {"right": [], "left": []}
    for k in sorted(target):
        for sd, sign in (("right", -1), ("left", +1)):
            if sd not in target[k]:
                continue
            want_xz = (S[k][0] + NS[k][0] * target[k][sd][0], S[k][2] + NS[k][1] * target[k][sd][0])
            got_xz = (B[k][0] + NB[k][0] * sign * W[k] / 2.0, B[k][2] + NB[k][1] * sign * W[k] / 2.0)
            # across the road only: a built vertex slides along the line as the shift changes, which moves no edge
            res[sd].append(round(abs((got_xz[0] - want_xz[0]) * NS[k][0] + (got_xz[1] - want_xz[1]) * NS[k][1]), 4))
    changed = [k for k in range(len(P)) if abs(pre[k][0] - P[k][0]) > 1e-4 or abs(pre[k][2] - P[k][2]) > 1e-4
               or abs(W[k] - widths[k]) > 1e-4]
    for k in changed:
        t_ = target.get(k, {})
        rows.append({"k": k, "line_xz": [round(P[k][0], 4), round(P[k][2], 4)], "width_was_m": round(widths[k], 3),
                     "new_xz": [round(pre[k][0], 4), round(pre[k][2], 4)], "width_m": W[k], "s_built_m": round(st[k], 2),
                     "right_u_m": None if "right" not in t_ else round(t_["right"][0], 3),
                     "left_u_m": None if "left" not in t_ else round(t_["left"][0], 3),
                     "weight": {sd: round(t_[sd][2], 3) for sd in t_}})
    rep = {"rows": len(rows), "vertices": [rows[0]["k"], rows[-1]["k"]] if rows else [],
           "width_m": [round(min(r["width_m"] for r in rows), 2), round(max(r["width_m"] for r in rows), 2)] if rows else [],
           "shift_m": [round(min(D), 3), round(max(D), 3)],
           "built_edge_off_target_across_m": {sd: {"max": max(v) if v else None,
                                              "p95": sorted(v)[int(0.95 * (len(v) - 1))] if v else None}
                                         for sd, v in res.items()}}
    return rows, rep


def far_piece(stations, spec, name):
    """the far carriageway, one connector (module doc)"""
    span = [float(v) for v in spec["span"]]
    mf_u, L_u = series(stations, "median_far", 0), series(stations, "left_edge", 0, divided_only=True)
    mf_y, L_y = series(stations, "median_far", 1), series(stations, "left_edge", 1, divided_only=True)
    pts, ws, rows = [], [], []
    for st_ in stations:
        s = float(st_["s_lap"])
        if not (span[0] - 1e-6 <= s <= span[1] + 1e-6):
            continue
        a, b = at(mf_u, s), at(L_u, s)
        ya, yb = at(mf_y, s), at(L_y, s)
        uc, w = (a + b) / 2.0, b - a
        y = (ya + yb) / 2.0
        nx, nz = st_["normal_xz"]
        x, z = st_["xz"][0] + nx * uc, st_["xz"][1] + nz * uc
        pts.append([round(x, 3), round(y, 3), round(z, 3)])
        ws.append(round(w, 3))
        rows.append({"s_lap": s, "far_face_u_m": round(a, 3), "far_curb_u_m": round(b, 3), "y_m": round(y, 3)})
    if len(pts) < 2:
        raise SystemExit(f"[divided_road] far piece: fewer than 2 stations in span {span}")
    # the connector runs the far carriageway's own way (southbound: against the lap)
    con = {"name": name, "kind": "connector", "points_xyz_m": pts[::-1], "widths_m": ws[::-1], "open_ends": True,
           "measured": {"source": "the G10's lidar faces (median_far, left_edge)", "span_s_built_m": span}}
    rep = {"name": name, "points": len(pts), "width_m": [min(ws), max(ws)], "span_s_built_m": span}
    return con, rows, rep


def island_runs(stations, span):
    """the station runs (index ranges) where both median faces read a raised median (module doc)"""
    idx = [i for i, st_ in enumerate(stations) if span[0] - 1e-6 <= float(st_["s_lap"]) <= span[1] + 1e-6]
    ok = [i for i in idx if face_reading(stations[i], "median_near") and face_reading(stations[i], "median_far")]
    runs, cur = [], []
    for i in ok:
        if cur and i - cur[-1] > ISLAND_GAP_STATIONS + 1:
            runs.append(cur)
            cur = []
        cur.append(i)
    if cur:
        runs.append(cur)
    out = []
    for r in runs:
        if float(stations[r[-1]]["s_lap"]) - float(stations[r[0]]["s_lap"]) >= ISLAND_MIN_M:
            out.append(list(range(r[0], r[-1] + 1)))
    return out


def islands(stations, spec, id_prefix):
    span = [float(v) for v in spec["span"]]
    mn, mf = series(stations, "median_near", 0), series(stations, "median_far", 0)
    out, rep = [], []
    for n_, run in enumerate(island_runs(stations, span)):
        rows, ra, rb = [], [], []
        for i in run:
            st_ = stations[i]
            s = float(st_["s_lap"])
            a, b = at(mn, s) - ISLAND_ON_ROAD_M, at(mf, s) + ISLAND_ON_ROAD_M
            nx, nz = st_["normal_xz"]
            x0, z0 = st_["xz"]
            rows.append([round(x0 + nx * a, 3), round(z0 + nz * a, 3), round(x0 + nx * b, 3), round(z0 + nz * b, 3)])
            fa, fb = face_reading(st_, "median_near"), face_reading(st_, "median_far")
            if fa and fa[2] is not None:
                ra.append(fa[2])
            if fb and fb[2] is not None:
                rb.append(fb[2])
        med = lambda v: sorted(v)[len(v) // 2] if v else 0.0  # noqa: E731
        isl = {"id": f"{id_prefix}_{n_}", "rows": rows, "rise_m": [round(med(ra), 3), round(med(rb), 3)],
               "s_built_m": [float(stations[run[0]]["s_lap"]), float(stations[run[-1]]["s_lap"])]}
        out.append(isl)
        rep.append({"id": isl["id"], "rows": len(rows), "s_built_m": isl["s_built_m"], "rise_m": isl["rise_m"],
                    "rise_readings": [len(ra), len(rb)]})
    return out, rep


def lamp_posts(poles_rec, stations, spec, median_mid_u=None):
    """the measured light poles as scenery.streetlights.measured posts (tools/streetlight_relocate.measured_plan): each
    named pole's base as read, and out_xz, the unit the author steps it along when its footprint reaches a road: away
    from the lap for a curb-side pole, toward the median's middle for a median pole"""
    by = {p["id"]: p for p in poles_rec["poles"]}
    s_all = [float(st_["s_lap"]) for st_ in stations]
    posts = []
    for pid in spec["ids"]:
        p = by[pid]
        if not p.get("read"):
            raise SystemExit(f"[divided_road] lamps: pole {pid} is not read in the record")
        i = min(range(len(s_all)), key=lambda j: abs(s_all[j] - float(p["s"])))
        nx, nz = stations[i]["normal_xz"]
        u = float(p["u"])
        if p.get("side") == "median":
            mid = at(median_mid_u, float(p["s"])) if median_mid_u else u
            sign = -1.0 if u > mid else 1.0
        else:
            sign = 1.0 if u > 0 else -1.0
        posts.append({"id": pid, "base_xz": [float(v) for v in p["base_xz"]],
                      "out_xz": [round(sign * nx, 6), round(sign * nz, 6)], "s_built_m": float(p["s"]), "u_m": u,
                      "side": p.get("side"), "arms_seen": len(p.get("arms") or []),
                      "from_curb": p.get("from_curb")})
    return posts


def main(argv=None):
    a = list(sys.argv[1:] if argv is None else argv)
    write = "--write" in a
    if write:
        a.remove("--write")
    draft = None
    if "--draft" in a:
        i = a.index("--draft")
        draft = Path(a[i + 1])
        del a[i:i + 2]
    if len(a) != 1 or draft is None:
        print(__doc__)
        return 2
    port = Path(a[0])
    cfg = json.loads((port / "track.config.json").read_text(encoding="utf-8"))
    spec_all = json.loads((port / "source" / "divided_roads.json").read_text(encoding="utf-8"))
    raw = json.loads((draft / "data" / "centerline.raw.local.json").read_text(encoding="utf-8"))
    pts, widths = raw["points_xyz_m"], [float(w) for w in raw["widths_m"]]
    closed = math.hypot(pts[0][0] - pts[-1][0], pts[0][2] - pts[-1][2]) < 1e-6
    for road in spec_all["roads"]:
        G = json.loads((port / road["stations_file"]).read_text(encoding="utf-8"))
        _S = _smooth_mod().smooth_centerline([tuple(float(c) for c in p) for p in pts],
                                             sigma_pts=float((cfg.get("route") or {}).get("smooth_sigma_pts", 2.0)),
                                             passes=int((cfg.get("route") or {}).get("smooth_passes", 2)), sigma_y_pts=0.0)
        stations = unwrapped(G["stretches"][road["stretch"]]["stations_list"], _stations(_S)[-1])
        rows, rep = carriageway(pts, widths, closed, stations, road["lap"], cfg.get("route") or {})
        con, far_rows, far_rep = far_piece(stations, road["far"], road["far"]["name"])
        isl, isl_rep = islands(stations, road["island"], road["island"]["id_prefix"])
        lamps = None
        if road.get("lamps"):
            lp = road["lamps"]
            poles = json.loads((port / lp["poles_file"]).read_text(encoding="utf-8"))
            mn_, mf_ = series(stations, "median_near", 0), series(stations, "median_far", 0)
            mid = {k: (mn_[k] + mf_[k]) / 2.0 for k in mn_ if k in mf_}
            lamps = {"_doc": "scenery.streetlights.measured (tools/author_lamps_blend.py measured_posts, "
                             "tools/streetlight_relocate.measured_plan): the draft's posts whose base lies in "
                             "zone_s_built_m (stations on the built line) give way to these posts. Bases: "
                             + poles.get("_source_line", "the DRAPP 2022 3-inch orthophoto (DRCOG), read by eye to about "
                                         "+-0.3 m") + "; positions only, the image is not published. A post whose "
                             "footprint + 0.46 m setback reaches a road steps along out_xz to the first clear spot, at "
                             "most max_move_m [invented, the Mac 2026-11-25], else it is left to drop_on_road.",
                     "credit": lp["credit"], "poles_file": lp["poles_file"],
                     "zone_s_built_m": lp["zone_s_built_m"], "max_move_m": lp.get("max_move_m", 0.75),
                     "step_m": lp.get("step_m", 0.05), "posts": lamp_posts(poles, stations, lp, mid)}
        prov = {"tool": "tools/divided_road.py", "road": road["id"], "stations_file": road["stations_file"],
                "stretch": road["stretch"], "draft_line": "data/centerline.raw.local.json of a draft at "
                + str(road.get("draft_note", "")), "origin": raw["origin"],
                "constants": {"MED_HALF_M": MED_HALF_M, "MIN_READ": MIN_READ, "GAP_M": GAP_M, "SMOOTH_M": SMOOTH_M,
                              "TAPER_M": road["lap"].get("taper_m", TAPER_M), "ISLAND_ON_ROAD_M": ISLAND_ON_ROAD_M,
                              "ISLAND_GAP_STATIONS": ISLAND_GAP_STATIONS, "ISLAND_MIN_M": ISLAND_MIN_M}}
        out = {
            road["lap"]["out"]: {"_doc": "tools/divided_road.py: the lap on its own carriageway (lm_intake.carriageway). "
                                 "Per row: the intake line's vertex k at line_xz with width_was_m moves to new_xz with "
                                 "width_m (the move pre-compensated for the assembler's smoothing); right_u_m / left_u_m "
                                 "= the built edges' targets about the built line (u + = left); weight = the span's "
                                 "raised cosine.", "provenance": prov, "spec": road["lap"], "report": rep, "rows": rows},
            road["far"]["out"]: {"_doc": "tools/divided_road.py: the far carriageway as its own side piece "
                                 "(lm_intake.side_pieces): appended to the port's side streets before their profiles.",
                                 "provenance": prov, "spec": road["far"], "report": far_rep, "stations": far_rows,
                                 "connectors": [con]},
            road["island"]["out"]: {"_doc": "tools/divided_road.py: the median islands (route.islands entries, "
                                    "tools/author_islands_blend.py), where both median faces read a raised median.",
                                    "provenance": prov, "spec": road["island"], "report": isl_rep, "islands": isl},
        }
        if lamps is not None:
            out[road["lamps"]["out"]] = dict(lamps, provenance=prov)
            print(f"[divided_road] {road['id']}: lamps {[(q['id'], q['side'], q['out_xz']) for q in lamps['posts']]}")
        print(f"[divided_road] {road['id']}: lap {rep['rows']} rows v{rep['vertices']}, width {rep['width_m']} m, "
              f"shift {rep['shift_m']} m; built edge off its target, across {rep['built_edge_off_target_across_m']}")
        print(f"[divided_road] {road['id']}: far piece {far_rep}")
        print(f"[divided_road] {road['id']}: islands {isl_rep}")
        if write:
            for rel, body in out.items():
                (port / rel).write_text(json.dumps(body, indent=1), encoding="utf-8")
                print(f"[divided_road] wrote {port / rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

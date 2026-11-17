"""A stretch of the lane re-traced to the measured pavement edge, short of every rail (ledger 0087 Q1; opt-in
lm_intake.edge_retrace).

Kevin, 2026-11-17: "Yes, widen Milford's front straight" (0087 §7 Q1: the trace's 16 m clamp holds the front straight,
s 0-150 and 4,530-4,890, narrower than the paving). Per side of the line the assembler will build (the intake's line through
its own smoothing, as tools/edge_fit.py), inside each declared span:
  measured  the pavement edge: per row the median of one sensor's edge points within +-MED_HALF_M, a Gaussian over the
            measured rows (never past a row's own median + MED_CAP_M), gaps up to GAP_M interpolated; the points are (source/edges/edge_evidence.json; "src", NAIP by default: on Milford's light
            front straight the lidar's intensity step reads 0.8-2.5 m inside the paving NAIP and the image show, and the
            trace itself is NAIP's), owned by their nearest row within ALONG_M along and SEARCH_IN_M inside / SEARCH_OUT_M
            outside today's edge (the painted lines and joins further in are not the edge)
  widen     the edge never moves in: max(today's edge, measured)
  rails     and never onto a rail: every rail of the side (config scenery.bespoke.rails, by key) is projected onto the rows;
            the edge stops clear_m short of its face (the face is the rail's polyline; the W bulges 6.3 cm toward the road:
            author_bespoke_blend RAIL_D). Past a rail's end the limit opens at RAIL_FLARE m per m, so the edge never steps
            at a rail end. A rail that stands inside today's edge pulls the edge in to it there (the rail stands whole)
  blend     outside each span the change fades to nothing over taper_m (a raised cosine); then each side is Gaussian
            smoothed (SMOOTH_M) and clamped to the rail limit again
The lane is +-width/2 about the line, so a side that moves alone moves the line: the line shifts (left - right)/2 along
its left normal and the width is left + right. Pure Python (the intake is stdlib only).
"""
from __future__ import annotations

import bisect
import math

from tools import edge_fit as _ef

ALONG_M = 1.0          # an evidence point within 1 m along of its row (edge_fit's)
SEARCH_IN_M = 1.0      # [invented] and at most 1 m inside today's edge (NAIP reads painted lines 2-3 m in: 5.2-5.9 m on 8.0)
SEARCH_OUT_M = 4.0     # [invented] and at most 4 m outside it (the evidence was searched +-3.5 m of the trace's edge)
MIN_POINTS = 8         # [invented] evidence points inside a row's window before it measures (fewer: today's edge stays)
RAIL_FLARE = 0.10      # [invented] past a rail's end its limit opens 0.1 m per m (1:10, a gentle flare)
RAIL_REACH_M = 40.0    # [invented] how far past its end a rail's limit reaches
SMOOTH_M = 3.0         # [invented] the final edge's Gaussian sigma (rows), against the soft corners of max / min
MED_HALF_M = 7.5       # [invented] the measured edge: the median of the points within +-7.5 m (NAIP's points cluster within
#                        +-0.1-0.2 m per 15 m along Milford's front straight; the lidar's intensity steps scatter 1-3 m)
MED_SMOOTH_M = 5.0     # [invented] then a Gaussian of 5 m over the rows that measured
MED_CAP_M = 0.3       # [invented] the smoothed edge stays within 0.3 m of the row's own median
GAP_M = 40.0           # [invented] a row with no reading takes the line between measured rows up to 40 m either side


def _stations(P):
    st = [0.0]
    for a, b in zip(P, P[1:]):
        st.append(st[-1] + math.hypot(b[0] - a[0], b[2] - a[2]))
    return st


def _in_span(s, a, b, lap):
    return (a <= s <= b) if a <= b else (s >= a or s <= b)


def _dist_out(s, a, b, lap):
    """distance from station s to the span [a, b] along the closed lap (0 inside)"""
    if _in_span(s, a, b, lap):
        return 0.0
    da = (a - s) % lap
    db = (s - b) % lap
    return min(da, db)


def retrace(pts, widths, closed, evidence, spans, rails, *, src="naip", clear_m=0.10, half=_ef.FIT_HALF_M,
            taper_m=60.0):
    """pts: the smoothed line [(x, y, z)] (closed: last == first); widths: per point; evidence: [[E, N, src, contrast]];
    spans: [[s0, s1]] stations on this line; rails: [{"key", "xz": [(x, z), ...]}] in the line's frame.
    Returns (new widths, per-point lateral shift of the line (+ = left), report)."""
    n = len(pts)
    m = n - 1 if closed else n
    P = pts[:m]
    st = _stations(P)
    lap = (st[-1] + math.hypot(P[0][0] - P[-1][0], P[0][2] - P[-1][2])) if closed else st[-1]
    T = _ef._normals(P, closed)
    hw = [w / 2.0 for w in widths[:m]]
    reach = taper_m + half + 5.0
    region = [i for i in range(m) if any(_dist_out(st[i], a, b, lap) <= reach for a, b in spans)]
    rset = set(region)
    cell = 8.0
    grid: dict = {}
    for i in region:
        grid.setdefault((int(P[i][0] // cell), int(P[i][2] // cell)), []).append(i)

    def own(x, z):
        bx, bz = int(x // cell), int(z // cell)
        best, bi = None, None
        for dx in (-2, -1, 0, 1, 2):              # +-16 m: an edge point or a rail stands up to ~12 m off the line
            for dz in (-2, -1, 0, 1, 2):
                for i in grid.get((bx + dx, bz + dz), ()):
                    d = (P[i][0] - x) ** 2 + (P[i][2] - z) ** 2
                    if best is None or d < best:
                        best, bi = d, i
        if bi is None:
            return None
        tx, tz = T[bi]
        ex, ez = x - P[bi][0], z - P[bi][2]
        return bi, ex * tx + ez * tz, ex * (-tz) + ez * tx          # row, along, lateral (+ = left)

    # the evidence, per side and sensor: (row, offset from the line)
    pts_by = {"left": {}, "right": {}}
    for e, nn, s_, _c in evidence:
        o = own(e, nn)
        if o is None:
            continue
        i, v, u = o
        if abs(v) > ALONG_M:
            continue
        side = "left" if u > 0 else "right"
        if not (hw[i] - SEARCH_IN_M <= abs(u) <= hw[i] + SEARCH_OUT_M):
            continue
        pts_by[side].setdefault(s_, []).append((i, abs(u)))
    # the rails' faces, per side: row -> the nearest face offset; each rail's row run for the flare past its ends
    lim = {"left": [None] * m, "right": [None] * m}
    rail_rep = []
    for r in rails:
        xs = r["xz"]
        rows_hit = {}
        for a, b in zip(xs, xs[1:]):
            L = math.dist(a, b)
            k = max(1, int(L / 0.5))
            for j in range(k + 1):
                t = j / k
                o = own(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
                if o is None:
                    continue
                i, v, u = o
                if abs(v) <= ALONG_M:
                    rows_hit.setdefault(i, []).append(u)
        if not rows_hit:
            rail_rep.append({"key": r["key"], "rows": 0})
            continue
        side = "left" if sum(sum(v) for v in rows_hit.values()) > 0 else "right"
        face = {i: min(abs(u) for u in v) for i, v in rows_hit.items()}
        for i, f in face.items():
            lim[side][i] = f - clear_m if lim[side][i] is None else min(lim[side][i], f - clear_m)
        # past its ends: the limit opens at RAIL_FLARE per m. The ends are the two rows either side of the largest gap
        # between the rail's rows round the lap (a rail across the seam, G2 over the S/F, has its ends there, not at 0 / lap)
        srt = sorted(face, key=lambda i: st[i])
        gaps = [((st[srt[(k + 1) % len(srt)]] - st[srt[k]]) % lap if closed else
                 (st[srt[k + 1]] - st[srt[k]] if k + 1 < len(srt) else 0.0), k) for k in range(len(srt))]
        _g, kg = max(gaps)
        first, last = srt[(kg + 1) % len(srt)], srt[kg]            # the rail runs first -> last in travel order
        s_first, s_last = st[first], st[last]
        for e_, ahead in ((first, False), (last, True)):
            for i in region:
                if i in face:
                    continue
                d = (st[i] - st[e_]) % lap if ahead else (st[e_] - st[i]) % lap
                if d > RAIL_REACH_M:
                    continue
                v_ = face[e_] - clear_m + RAIL_FLARE * d
                lim[side][i] = v_ if lim[side][i] is None else min(lim[side][i], v_)
        rail_rep.append({"key": r["key"], "side": side, "rows": len(face),
                         "s_m": [round(s_first, 1), round(s_last, 1)],
                         "face_off_line_m": [round(min(face.values()), 2), round(max(face.values()), 2)]})
    # the measured edge per side: the robust LOESS through the chosen sensor's points
    rep = {"src": src, "clear_m": clear_m, "taper_m": taper_m, "fit_half_m": half, "spans": spans, "rails": rail_rep,
           "sides": {}, "rows": []}
    new_half = {}
    measured = {}
    for side in ("left", "right"):
        pts_s = pts_by[side].get(src, [])
        # THE MEASURED EDGE: per row the median of the sensor's points owned by rows within +-MED_HALF_M (a median, not a
        # fit: near the S/F NAIP reads a second population ~1.7 m inside the edge, 30 % of the points, and a robust
        # quadratic flips between the two), then a normalised Gaussian (MED_SMOOTH_M) over the rows that measured, and
        # rows with no reading interpolated between the nearest measured rows within GAP_M (else today's edge stays)
        by_row: dict = {}
        for i, u in pts_s:
            by_row.setdefault(i, []).append(u)
        own_rows = sorted(by_row, key=lambda i: st[i])
        S_ = [st[i] for i in own_rows]
        med = {}
        for i in region:
            vals = []
            for s0 in (st[i] - lap, st[i], st[i] + lap) if closed else (st[i],):
                lo = bisect.bisect_left(S_, s0 - MED_HALF_M)
                hi = bisect.bisect_right(S_, s0 + MED_HALF_M)
                for q in range(lo, hi):
                    vals.extend(by_row[own_rows[q]])
            if len(vals) >= MIN_POINTS:
                vals.sort()
                med[i] = vals[len(vals) // 2]
        f = {}
        sg_r = MED_SMOOTH_M
        for i in region:
            num = den = 0.0
            for j, v in med.items():
                d = abs(st[j] - st[i])
                d = min(d, lap - d) if closed else d
                if d <= 3 * sg_r:
                    kw = math.exp(-0.5 * (d / sg_r) ** 2)
                    num += kw * v
                    den += kw
            if den > 0.3:
                f[i] = num / den
                if i in med:                      # never past the row's own median + MED_CAP_M: the Gaussian spills
                    f[i] = min(f[i], med[i] + MED_CAP_M)   # across a real narrowing (s 4,690: 9.6 -> 6.9 m in 10 m)
        # gaps: linear between the nearest rows with a value, within GAP_M either side
        have = sorted(f, key=lambda i: st[i])
        hs = [st[i] for i in have]
        for i in region:
            if i in f or not have:
                continue
            k_ = bisect.bisect_left(hs, st[i])
            a_, b_ = have[k_ - 1] if k_ > 0 else None, have[k_] if k_ < len(have) else None
            if a_ is None or b_ is None:
                continue
            da, db = st[i] - st[a_], st[b_] - st[i]
            if da <= GAP_M and db <= GAP_M and da + db > 0:
                f[i] = f[a_] + (f[b_] - f[a_]) * da / (da + db)
        measured[side] = f
        tgt = list(hw)
        for i in region:
            d = min(_dist_out(st[i], a, b, lap) for a, b in spans)
            w_ = 1.0 if d <= 0 else (0.5 + 0.5 * math.cos(math.pi * d / taper_m) if d < taper_m else 0.0)
            want = max(hw[i], f.get(i, hw[i]))
            if lim[side][i] is not None:
                want = min(want, lim[side][i])
            tgt[i] = hw[i] + w_ * (want - hw[i])
        # Gaussian smoothing over the region (rows), then the rail limit again
        sg = SMOOTH_M
        rr = int(3 * sg) + 1
        out = list(tgt)
        for i in region:
            num = den = 0.0
            for q in range(-rr, rr + 1):
                j = (i + q) % m if closed else i + q
                if not (0 <= j < m):
                    continue
                kw = math.exp(-0.5 * (q / sg) ** 2)
                num += kw * tgt[j]
                den += kw
            out[i] = min(num / den, tgt[i] + 0.15)     # the smoothing rounds corners; it never lifts an edge 0.15 m
            if lim[side][i] is not None:                # past its own target (it spilled across s 4,690's narrowing)
                out[i] = min(out[i], lim[side][i])
        new_half[side] = out
        moved = [out[i] - hw[i] for i in region]
        rep["sides"][side] = {"rows_measured": len(med), "points": len(pts_s),
                              "other_sensors": {k: len(v) for k, v in pts_by[side].items() if k != src},
                              "moved_m": {"min": round(min(moved), 3), "max": round(max(moved), 3)}}
    shift = [0.0] * n
    new_w = list(widths)
    for i in range(m):
        L, R = new_half["left"][i], new_half["right"][i]
        shift[i] = (L - R) / 2.0
        new_w[i] = round(L + R, 3)
    if closed:
        shift[-1], new_w[-1] = shift[0], new_w[0]
    # the per-row record (every row of the spans + taper): today's edges, each sensor's reading, the rail faces, the new edges

    def _med(side, sname, i):
        v = sorted(u for j, u in pts_by[side].get(sname, []) if abs(st[j] - st[i]) <= 5.0 or lap - abs(st[j] - st[i]) <= 5.0)
        return round(v[len(v) // 2], 2) if len(v) >= 3 else None
    for i in region:
        if i % 2:
            continue
        rep["rows"].append({"s": round(st[i], 1), "old_half_m": round(hw[i], 3),
                            "new_left_m": round(new_half["left"][i], 3), "new_right_m": round(new_half["right"][i], 3),
                            "fit_left_m": round(measured["left"][i], 3) if i in measured["left"] else None,
                            "fit_right_m": round(measured["right"][i], 3) if i in measured["right"] else None,
                            "naip_left_m": _med("left", "naip", i), "lidar_left_m": _med("left", "lidar", i),
                            "naip_right_m": _med("right", "naip", i), "lidar_right_m": _med("right", "lidar", i),
                            "rail_left_limit_m": None if lim["left"][i] is None else round(lim["left"][i], 3),
                            "rail_right_limit_m": None if lim["right"][i] is None else round(lim["right"][i], 3),
                            "shift_m": round(shift[i], 3), "width_old_m": round(2 * hw[i], 2), "width_new_m": new_w[i]})
    ws = [(new_w[i] - widths[i]) for i in region]
    rep["width_change_m"] = {"min": round(min(ws), 2), "max": round(max(ws), 2)}
    rep["shift_m"] = {"min": round(min(shift[i] for i in region), 3), "max": round(max(shift[i] for i in region), 3)}
    return new_w, shift, rep


def rails_in_frame(cfg_rails, keys, origin):
    """the named rails' polylines (config scenery.bespoke.rails, lon / lat) in the line's local frame (x = E, z = N),
    by the same WGS84 series as scripts.geometry.projection._meters_per_degree"""
    phi = math.radians(origin["lat"])
    m_lat = 111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
    m_lon = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi)
    by = {r["key"]: r for r in cfg_rails}
    missing = [k for k in keys if k not in by]
    if missing:
        raise SystemExit(f"[edge_retrace] no such rail(s) in scenery.bespoke.rails: {missing}")
    return [{"key": k, "xz": [((lo - origin["lon"]) * m_lon, (la - origin["lat"]) * m_lat)
                              for lo, la in by[k]["polyline_lonlat"]]} for k in keys]

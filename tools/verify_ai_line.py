"""Gate: a written AI line against the BUILT layout it will be driven on (ledger 0052).

Kevin, 2026-10-12, after a 7-AI race on the v0.17.1 race layouts: "ai races need tuning, they tend to crash
and slow down weirdlu". The drafts aimed at the K-rail (1.50 m from a wall face, a car is ~1.9 m wide),
braked for bends that were not there (a payload radius pinched below the line's own shape), and carried five
payload fields in a meaning no reference line on this PC uses. Nothing in the ship chain measured a written
line against the walls the car would hit (ai_draft.json judges it against the writer's own declaration). This
does, on the line AS WRITTEN (``fast_lane.ai``, kn5 frame) and the BUILT gate OBJ (``data/track.<layout>.obj``,
engine frame: the road + race + that layout's closure kn5) — L5.

    python tools/verify_ai_line.py <project> --layout race_cw [--ai <fast_lane.ai>] [--obj <gate.obj>] [--out <json>]
                                   [--baseline <the line it replaces>]

Exit 1 on FAIL. Writes ``data/ai_verify.<layout>.json`` (default). Thresholds (fleet/GATES-CHANGELOG.md, the
ledger-0052 section; overridable per track in ``track.config.json`` ``ai.verify``):

  V1 payload semantics: what AC's own lines carry. MEASURED = V1 passes on every one of the 34 Kunos lines
     installed on this PC (the sign rules also on ~90 third-party lines) — ledger 0052, scratch kunos_v1.txt.
     AC's lines come in two FAMILIES, told apart by the length field: the SEGMENT family (33 of the 34 Kunos lines,
     and what write_ai_line writes) and the WINDOW family (ks_silverstone/international and 33 third-party lines:
     length = the last 5 segments summed, radius through the points +-5, a direction ramp 0 ... 0.9 over the 10
     points at each end of the lap, the normal stored as (0,1,0)). A line is judged by its own family's rules.
     length       median |length - the family's reference| < 0.01 m; segment family also <= 0.1 m on every point
                  but the last (Kunos: max 0.056 m; the last point carries ~5 x the spacing on every Kunos line).
                  A spacing GAP is not a payload error (most Kunos lines have a ~4.6 m one, its length field
                  matching it): reported, not gated.
     direction    +-1 on every point but the last (segment family: 0.1 there on 13 of 33, the recorder's seam
                  point) / but the seam ramps (window family); = -sign(LOCAL heading change, +-1 point) on >= 99 %
                  of points turning > 0.5 deg (Kunos 99.77-100 %; at +-10 points only 96.8-99.5 %)
     header       lapTime = sampleCount = 0
     radius       = the family's circumradius (3-point / +-5 points): median |ln(field / circumradius)| < 0.01
     camber       segment family: = the BUILT 1ROAD surface's tilt under the point measured toward the bend,
                  -direction x asin(normal . right) (the sign rule of every reference line: 0.95-1.00 of tilted
                  points; plain asin(normal . right) agrees on ~0.5): median ratio 0.9-1.1 where the road tilts
                  > 0.01 rad (else median |difference| < 0.005 rad [INVENTED]); the normal is not (0,1,0)
                  everywhere. Window family: not judged (Kunos' own stores the normal up beside a real camber).
  V2 wall clearance: the line's centre to the nearest BUILT 1WALL face (horizontal, layer band -2/+4 m)
     min >= 2.0 m [INVENTED: the two walled Kunos references measured are ks_monza66 1.981 and
     ks_black_cat_county 2.066, so 2.0 is a choice between them]; lap under 2.5 m <= 1.0 % [INVENTED]
  V3 no phantom corners (the SPURIOUS-DIP definition): a physics speed profile (mu 1.0, braking 0.9 g, accel
     0.35 g, 250 km/h cap) from the payload radius field vs the same profile from the line's car-scale radius
     (circumradius through the points +-4 = +-6 m). A point where the payload profile is > 10 % slower is a
     spurious dip: 0 allowed [INVENTED for a GENERATED line: 20 of the 34 Kunos lines have 0, the other 14 have
     5-885 — AC's own recorder leaves them, so a dip is the defect class the 0052 drafts showed (160 / 875 of
     them), not a proof that the AI brakes there]. Bend flips (car-scale curvature |k| > 1/300 changing sign
     within 30 m) <= 0.75 / km [INVENTED: Kunos 0-1.24 / km].
  V4 sides: 0 points whose sideLeft / sideRight reaches past the first BUILT wall a horizontal ray meets on that
     side (perpendicular to the line) [INVENTED].
  V5 the line's own 3-point radius >= 11.4 m [INVENTED: the writer's RADIUS_FLOOR_M 12 x its RADIUS_CHECK 0.95].
  V6 (with --baseline = the line this one replaces) every corner the baseline has (a car-scale radius that is the
     minimum within +-60 points and under 80 m) keeps >= 0.85 x that radius on this line: its car-scale minimum
     over +-60 points round its nearest point [INVENTED: the 0052 diagnosis' pre-declared box rule].

A CSP recording is not put through this gate by the ship chain (it replaces the draft file-for-file, ledger 0023).
Run on one, V1 is a check every Kunos line passes (either family); V2-V6 are standards set for a GENERATED line.
Reported, not gated: the lap-time estimate of both profiles, where each check is worst. The judge is still the
race (rule 0): a GENERATED draft stays a draft under ledger 0023 however green this is.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.ac.ai_built import RoadSurface, WallIndex, read_ai, read_gate_obj  # noqa: E402

G = 9.81
DEFAULTS = {
    # V1 — MEASURED = passes every one of the 34 Kunos lines installed on this PC (scratch kunos/kunos_v1.txt)
    "length_med_err_max_m": 0.01,        # MEASURED (Kunos 0.0000-0.0016 segment family, 0.0009 window family)
    "length_pt_err_max_m": 0.1,          # MEASURED (Kunos segment family max 0.056 m, every point but the last)
    "window_family_pts": 5,              # MEASURED (the window family: length = 5 segments, radius through +-5)
    "seam_ramp_pts": 10,                 # MEASURED (window family: direction 0, 0.1 ... 0.9 over 10 points per end)
    "direction_agree_min": 0.99,         # MEASURED (Kunos 0.9977-1.0 at +-1 point)
    "direction_window_pts": 1,           # +-1 point: the local turn (Kunos' definition; at +-10: 0.968-0.995)
    "direction_turn_min_deg": 0.5,       # INVENTED measuring parameter (a bend, not float noise)
    "radius_med_log_err_max": 0.01,      # MEASURED (Kunos 0.0001-0.0034)
    "camber_ratio_lo": 0.9,              # MEASURED (Kunos segment family median ratio 0.998-1.001)
    "camber_ratio_hi": 1.1,
    "camber_tilt_min_rad": 0.01,         # INVENTED measuring parameter (a tilted road, ~0.6 deg)
    "camber_flat_med_err_max_rad": 0.005,  # INVENTED (on a flat road: passes every Kunos segment-family line)
    # V2-V6 — INVENTED: chosen against the references named, not met by every one of them
    "wall_min_m": 2.0,                   # INVENTED (Kunos walled references: ks_monza66 1.981, ks_black_cat_county 2.066)
    "wall_band_m": 2.5,
    "under_band_max_frac": 0.01,         # INVENTED (BCC 0.58 %, Monza66 3.2 %)
    "dip_frac": 0.10,                    # a payload-profile point > 10 % slower than the car-scale profile ...
    "dip_pts_max": 0,                    # ... INVENTED for a generated line (Kunos: 0 on 20 of 34, 5-885 on 14)
    "car_scale_pts": 4,                  # +-4 points = +-6 m at 1.5 m spacing
    "mu": 1.0, "decel_g": 0.9, "accel_g": 0.35, "vmax_ms": 69.4,   # INVENTED profile model (reported lap estimates)
    "flip_k_min": 1.0 / 300.0,
    "flip_window_m": 30.0,
    "flips_per_km_max": 0.75,            # INVENTED (Kunos 0-1.24 / km)
    "side_overreach_pts_max": 0,         # INVENTED (geometry: a side past a built wall points the AI at it)
    "radius_min_m": 11.4,                # INVENTED (write_ai_line RADIUS_FLOOR_M 12 x RADIUS_CHECK 0.95)
    "box_keep_min": 0.85,                # INVENTED (the 0052 diagnosis' box rule): V6, with --baseline only
    "box_corner_r_max_m": 80.0,          # V6: a baseline corner = a +-box_window_pts car-scale radius minimum under this
    "box_window_pts": 60,
}


def _circum_xz(a, b, c) -> float:
    ax, az, bx, bz, cx, cz = a[0], a[2], b[0], b[2], c[0], c[2]
    ab = math.hypot(bx - ax, bz - az)
    bc = math.hypot(cx - bx, cz - bz)
    ca = math.hypot(ax - cx, az - cz)
    cr = abs((bx - ax) * (cz - az) - (bz - az) * (cx - ax))
    if cr < 1e-12:
        return 1e9
    return ab * bc * ca / (2.0 * cr)


def _median(v):
    s = sorted(v)
    if not s:
        return None
    m = len(s) // 2
    return s[m] if len(s) % 2 else 0.5 * (s[m - 1] + s[m])


def turns(pos) -> list[float]:
    """Signed horizontal heading change (radians) at every point of a closed line: heading of segment i -> i+1
    minus that of i-1 -> i, heading = atan2(dz, dx) in the frame the points are in."""
    n = len(pos)
    h = [math.atan2(pos[(i + 1) % n][2] - pos[i][2], pos[(i + 1) % n][0] - pos[i][0]) for i in range(n)]
    return [((h[i] - h[i - 1] + math.pi) % (2.0 * math.pi)) - math.pi for i in range(n)]


def window_sum(v, k: int) -> list[float]:
    n = len(v)
    s = sum(v[j % n] for j in range(-k, k + 1))
    out = []
    for i in range(n):
        out.append(s)
        s += v[(i + k + 1) % n] - v[(i - k) % n]
    return out


def speed_profile(R, ds: float, mu: float, decel_g: float, accel_g: float, vmax: float) -> list[float]:
    """mu-limited corner speeds, then braking (backward) and acceleration (forward) passes, closed lap."""
    n = len(R)
    v = [min(vmax, math.sqrt(mu * G * max(r, 0.1))) for r in R]
    for _ in range(2):
        for i in range(n - 1, -1, -1):
            v[i] = min(v[i], math.sqrt(v[(i + 1) % n] ** 2 + 2.0 * decel_g * G * ds))
    for _ in range(2):
        for i in range(n):
            v[i] = min(v[i], math.sqrt(v[i - 1] ** 2 + 2.0 * accel_g * G * ds))
    return v


def _runs(flags, values=None, limit: int = 30) -> list[dict]:
    out, n, i = [], len(flags), 0
    while i < n and len(out) < limit:
        if flags[i]:
            j = i
            while j + 1 < n and flags[j + 1]:
                j += 1
            r = {"from": i, "to": j, "pts": j - i + 1}
            if values is not None:
                k = min(range(i, j + 1), key=lambda q: values[q])
                r.update(worst=k, value=round(values[k], 3))
            out.append(r)
            i = j + 1
        else:
            i += 1
    return out


def measure(ai: dict, *, walls: WallIndex | None, road: RoadSurface | None, th: dict) -> dict:
    """Every V1-V5 number for a decoded closed line (``read_ai``). ``walls`` / ``road`` from the gate OBJ (None:
    those checks are reported as not run, and FAIL)."""
    P = ai["pos"]
    n = len(P)
    seg = [math.dist(P[i], P[i - 1]) for i in range(n)]               # 3D, point i's segment from i-1 (0: the seam)
    ds = _median(seg)
    lap_m = sum(seg)
    m: dict = {"points": n, "spacing_m": round(ds, 4), "lap_m": round(lap_m, 1)}

    # --- V1 payload semantics -------------------------------------------------------------------------------
    v1: dict = {"header_lap_ms": ai["lap_ms"], "header_sample_count": ai["sample_count"], "has_grid": ai["has_grid"]}
    if "length" not in ai:
        v1["error"] = "no extras block"
        m["v1"] = v1
        return m
    L = ai["length"]
    # AC's lines come in two families (every line on this PC is one or the other): the SEGMENT family (33 of the
    # 34 Kunos lines; what write_ai_line writes) stores length = the point's own segment and radius = the 3-point
    # circumradius; the WINDOW family (ks_silverstone/international and 33 third-party lines) stores length = the
    # last window_family_pts segments summed and radius = the circumradius through the points +-that many, with a
    # direction ramp (0, 0.1 ... 0.9) over the seam_ramp_pts first / last points. The length field says which.
    kw = int(th["window_family_pts"])
    segw = [sum(seg[i - j] for j in range(kw)) for i in range(n)]
    e_seg = _median([abs(L[i] - seg[i]) for i in range(n)])
    e_win = _median([abs(L[i] - segw[i]) for i in range(n)])
    window = e_win < e_seg and e_win < th["length_med_err_max_m"]     # matches neither: judged as a segment line
    v1["family"] = "window" if window else "segment"
    ref = segw if window else seg
    v1["length_med_err_m"] = round(e_win if window else e_seg, 5)
    v1["length_max_m"] = round(max(L), 3)
    # every point but the last (AC's own lines carry ~5 x the spacing there): length = that point's own segment.
    # The window family is not judged point by point (Kunos' own carries up to 1.48 m away from its seam)
    lerr = [abs(L[i] - ref[i]) for i in range(n - 1)]
    v1["length_off_segment_pts"] = 0 if window else sum(1 for e in lerr if e > th["length_pt_err_max_m"])
    v1["length_pt_err_max_m"] = round(max(lerr), 4) if lerr else None
    v1["spacing_gaps_over_3x"] = sum(1 for i in range(1, n) if seg[i] > 3.0 * ds)   # reported (Kunos: one each)
    d = ai["direction"]
    # every point but the last (segment family: AC carries 0.1 there, the recorder's seam point); the window
    # family's seam ramp (seam_ramp_pts each end) is not judged either
    ramp = int(th["seam_ramp_pts"]) if window else 0
    judged = range(ramp, n - max(1, ramp))
    v1["direction_not_unit_pts"] = sum(1 for i in judged if abs(abs(d[i]) - 1.0) > 1e-6)
    tk = window_sum(turns(P), int(th["direction_window_pts"]))
    big = [i for i in judged if abs(tk[i]) > math.radians(th["direction_turn_min_deg"])]
    agree = sum(1 for i in big if d[i] == -math.copysign(1.0, tk[i]))
    v1["direction_agree"] = round(agree / len(big), 4) if big else None
    R1 = [_circum_xz(P[i - 1], P[i], P[(i + 1) % n]) for i in range(n)]
    Rf = R1 if not window else [_circum_xz(P[(i - kw) % n], P[i], P[(i + kw) % n]) for i in range(n)]
    rf = ai["radius"]
    errs = [abs(math.log(rf[i]) - math.log(min(max(Rf[i], 1.0), 1e9))) for i in range(n) if 1.0 < rf[i] < 3000.0 and Rf[i] < 1e8]
    v1["radius_med_log_err"] = round(_median(errs), 5) if errs else None
    # camber vs the BUILT surface: the normal under the point (engine frame -> kn5: z negated), right = (-fz, 0, fx).
    # The window family's camber is not judged: Kunos' own (ks_silverstone/international) stores the normal as
    # (0,1,0) beside a non-zero camber, so no reference shows what it is measured from
    if window:
        v1["camber_not_judged"] = "window family: no Kunos reference to measure its camber against"
    if road is not None:
        tilts, cams, missing = [], [], 0
        for i in range(n):
            x, y, z = P[i]
            s = road.sample(x, y, -z)
            if s is None:
                missing += 1
                continue
            nx, ny, nz = s[1][0], s[1][1], -s[1][2]
            fx, fz = ai["fx"][i], ai["fz"][i]
            rl = math.hypot(fx, fz) or 1.0
            # the tilt measured toward the bend, -direction x asin(n . right): AC's sign rule
            tilts.append(-ai["direction"][i] * math.asin(max(-1.0, min(1.0, (nx * -fz + nz * fx) / rl))))
            cams.append(ai["camber"][i])
        v1["camber_points_off_road"] = missing
        tilted = [(c, t) for c, t in zip(cams, tilts) if abs(t) > th["camber_tilt_min_rad"]]
        v1["camber_tilted_points"] = len(tilted)
        v1["camber_ratio_med"] = round(_median([c / t for c, t in tilted]), 4) if tilted else None
        v1["camber_med_abs_err_rad"] = round(_median([abs(c - t) for c, t in zip(cams, tilts)]), 5) if cams else None
        v1["built_tilt_max_rad"] = round(max((abs(t) for t in tilts), default=0.0), 4)
    v1["normal_ny_min"] = round(min(ai["ny"]), 6)
    m["v1"] = v1

    # --- V2 wall clearance ----------------------------------------------------------------------------------
    clear = None
    if walls is not None:
        clear = [walls.nearest(x, y, -z)[0] for x, y, z in P]
        under = [c < th["wall_band_m"] for c in clear]
        m["v2"] = {"min_m": round(min(clear), 3), "min_at": min(range(n), key=lambda i: clear[i]),
                   "under_2m_m": round(sum(seg[i] for i in range(n) if clear[i] < 2.0), 1),
                   "under_band_m": round(sum(seg[i] for i in range(n) if under[i]), 1),
                   "under_band_frac": round(sum(seg[i] for i in range(n) if under[i]) / lap_m, 5),
                   "runs_under_band": _runs(under, clear)}

    # --- V3 phantom corners ---------------------------------------------------------------------------------
    k = int(th["car_scale_pts"])
    R4 = [_circum_xz(P[(i - k) % n], P[i], P[(i + k) % n]) for i in range(n)]
    prof = dict(ds=ds, mu=th["mu"], decel_g=th["decel_g"], accel_g=th["accel_g"], vmax=th["vmax_ms"])
    v4 = speed_profile(R4, **prof)
    vf = speed_profile(rf, **prof)
    v1p = speed_profile(R1, **prof)
    dip = [(v4[i] - vf[i]) / v4[i] for i in range(n)]
    dipr = [(v4[i] - v1p[i]) / v4[i] for i in range(n)]
    t9 = window_sum(turns(P), 4)
    curv = [t / (9.0 * ds) for t in t9]
    flips, last = [], None
    for i in range(n):
        if abs(curv[i]) > th["flip_k_min"]:
            sgn = 1 if curv[i] > 0 else -1
            if last is not None and sgn != last[0] and (i - last[1]) * ds < th["flip_window_m"]:
                flips.append(i)
            last = (sgn, i)
    m["v3"] = {"dip_pts": sum(1 for x in dip if x > th["dip_frac"]),
               "dip_pts_3pt_radius": sum(1 for x in dipr if x > th["dip_frac"]),
               "dip_runs": [dict(r, v_payload_kmh=round(vf[r["worst"]] * 3.6, 1), v_car_scale_kmh=round(v4[r["worst"]] * 3.6, 1))
                            for r in _runs([x > th["dip_frac"] for x in dip], [-x for x in dip], 20)],
               "worst_dip_frac": round(max(dip), 4),
               "flips": len(flips), "flips_per_km": round(len(flips) / (lap_m / 1000.0), 3), "flip_at": flips[:30],
               "lap_s_car_scale": round(sum(seg[i] / v4[i] for i in range(n)), 1),
               "lap_s_payload_radius": round(sum(seg[i] / vf[i] for i in range(n)), 1),
               "vmin_kmh_car_scale": round(min(v4) * 3.6, 1), "vmin_kmh_payload": round(min(vf) * 3.6, 1)}

    # --- V4 sides vs the built walls ------------------------------------------------------------------------
    if walls is not None:
        over, worst, at = 0, 0.0, None
        per_side = {"left": 0, "right": 0}
        gaps = []
        for i in range(n):
            x, y, z = P[i]
            fx, fz = ai["fx"][i], -ai["fz"][i]                    # engine frame forward
            fl = math.hypot(fx, fz) or 1.0
            rx, rz = fz / fl, -fx / fl                              # engine right of travel (tz, -tx)
            for side, sx, sz, w in (("left", -rx, -rz, ai["side_left"][i]), ("right", rx, rz, ai["side_right"][i])):
                hit = walls.ray(x, y, -z, sx, sz, w + 3.0)
                if hit < float("inf"):
                    gaps.append(hit - w)
                if hit < w:
                    over += 1
                    per_side[side] += 1
                    if w - hit > worst:
                        worst, at = w - hit, i
        m["v4"] = {"overreach_pts": over, "per_side": per_side, "worst_m": round(worst, 3), "worst_at": at,
                   "side_max_m": round(max(max(ai["side_left"]), max(ai["side_right"])), 2),
                   "sides_with_a_wall_within_3m_beyond": len(gaps),
                   "median_gap_side_to_wall_m": round(_median(gaps), 3) if gaps else None}

    # --- V5 ---------------------------------------------------------------------------------------------------
    m["v5"] = {"min_radius_m": round(min(R1), 2), "min_radius_at": min(range(n), key=lambda i: R1[i])}
    return m


def judge(m: dict, th: dict) -> list[str]:
    """The FAIL reasons (empty = PASS)."""
    f: list[str] = []
    v1 = m.get("v1", {})
    if "error" in v1:
        return [f"V1 {v1['error']}"]
    if v1["length_med_err_m"] >= th["length_med_err_max_m"]:
        f.append(f"V1 length is not the segment length, nor AC's {th['window_family_pts']}-segment window (median error "
                 f"{v1['length_med_err_m']} m)")
    if v1["length_off_segment_pts"]:
        f.append(f"V1 {v1['length_off_segment_pts']} points carry a length > {th['length_pt_err_max_m']} m off their own "
                 f"segment (worst {v1['length_pt_err_max_m']} m)")
    if v1["direction_not_unit_pts"]:
        f.append(f"V1 direction is not +-1 on {v1['direction_not_unit_pts']} points")
    if v1["direction_agree"] is not None and v1["direction_agree"] < th["direction_agree_min"]:
        f.append(f"V1 direction agrees with the bend on {v1['direction_agree']:.1%} of bending points")
    if v1["header_lap_ms"] != 0 or v1["header_sample_count"] != 0:
        f.append(f"V1 header lapTime/sampleCount {v1['header_lap_ms']}/{v1['header_sample_count']} (Kunos: 0/0)")
    if v1["radius_med_log_err"] is None or v1["radius_med_log_err"] >= th["radius_med_log_err_max"]:
        f.append(f"V1 radius field is not the {v1['family']} family's circumradius (median |ln| error {v1['radius_med_log_err']})")
    if "camber_not_judged" in v1:
        pass
    elif "camber_med_abs_err_rad" not in v1:
        f.append("V1 camber not judged: no built 1ROAD surface")
    elif v1["camber_tilted_points"]:
        r = v1["camber_ratio_med"]
        if not th["camber_ratio_lo"] <= r <= th["camber_ratio_hi"]:
            f.append(f"V1 camber / built tilt median ratio {r} outside {th['camber_ratio_lo']}-{th['camber_ratio_hi']}")
        if v1["normal_ny_min"] >= 1.0 - 1e-6:
            f.append("V1 normal is (0,1,0) everywhere on a tilted road")
    elif v1["camber_med_abs_err_rad"] is None or v1["camber_med_abs_err_rad"] >= th["camber_flat_med_err_max_rad"]:
        f.append(f"V1 camber differs from the built tilt (median {v1['camber_med_abs_err_rad']} rad)")
    if "v2" not in m:
        f.append("V2 wall clearance not judged: no built walls")
    else:
        v2 = m["v2"]
        if v2["min_m"] < th["wall_min_m"]:
            f.append(f"V2 the line passes {v2['min_m']} m from a built wall (min {th['wall_min_m']} m) at point {v2['min_at']}")
        if v2["under_band_frac"] > th["under_band_max_frac"]:
            f.append(f"V2 {v2['under_band_frac']:.2%} of the lap within {th['wall_band_m']} m of a wall (max {th['under_band_max_frac']:.1%})")
    v3 = m["v3"]
    if v3["dip_pts"] > th["dip_pts_max"]:
        f.append(f"V3 {v3['dip_pts']} spurious speed dips (payload radius > {th['dip_frac']:.0%} slower than the car-scale line)")
    if v3["flips_per_km"] > th["flips_per_km_max"]:
        f.append(f"V3 {v3['flips_per_km']} bend flips within {th['flip_window_m']:g} m per km (max {th['flips_per_km_max']})")
    if "v4" not in m:
        f.append("V4 sides not judged: no built walls")
    elif m["v4"]["overreach_pts"] > th["side_overreach_pts_max"]:
        f.append(f"V4 {m['v4']['overreach_pts']} side widths reach past a built wall (worst {m['v4']['worst_m']} m at {m['v4']['worst_at']})")
    if m["v5"]["min_radius_m"] < th["radius_min_m"]:
        f.append(f"V5 the line's radius {m['v5']['min_radius_m']} m < {th['radius_min_m']} m at point {m['v5']['min_radius_at']}")
    for c in (m.get("v6") or {}).get("corners", []):
        if c["ratio"] < th["box_keep_min"]:
            f.append(f"V6 the corner at baseline point {c['baseline_at']} keeps {c['ratio']} x its radius "
                     f"({c['baseline_r_m']} -> {c['r_m']} m; min {th['box_keep_min']})")
    return f


def corners_vs_baseline(ai: dict, base: dict, th: dict) -> dict:
    """V6: every corner of ``base`` (a car-scale radius that is the minimum within +-box_window_pts and under
    box_corner_r_max_m) against this line's car-scale minimum over the same window round its nearest point."""
    k, wpts = int(th["car_scale_pts"]), int(th["box_window_pts"])

    def r_car(P):
        n = len(P)
        return [_circum_xz(P[(i - k) % n], P[i], P[(i + k) % n]) for i in range(n)]
    P, B = ai["pos"], base["pos"]
    rp, rb = r_car(P), r_car(B)
    nb, n = len(B), len(P)
    out = []
    for i in range(nb):
        if rb[i] >= th["box_corner_r_max_m"]:
            continue
        # the first point of the lowest radius within the window (ties go to the earliest)
        if any(rb[(i + d) % nb] < rb[i] or (rb[(i + d) % nb] == rb[i] and d < 0) for d in range(-wpts, wpts + 1) if d):
            continue
        j = min(range(n), key=lambda q: (P[q][0] - B[i][0]) ** 2 + (P[q][2] - B[i][2]) ** 2)
        r_new = min(rp[(j + d) % n] for d in range(-wpts, wpts + 1))
        out.append({"baseline_at": i, "at": j, "baseline_r_m": round(rb[i], 2), "r_m": round(r_new, 2),
                    "ratio": round(r_new / rb[i], 3)})
    return {"corners": out, "min_ratio": min((c["ratio"] for c in out), default=None)}


def thresholds(project: Path | None, overrides: dict | None = None) -> dict:
    th = dict(DEFAULTS)
    if project is not None and (project / "track.config.json").exists():
        cfg = json.loads((project / "track.config.json").read_text(encoding="utf-8"))
        th.update(((cfg.get("ai") or {}).get("verify") or {}))
    th.update(overrides or {})
    return th


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Gate a written AI line against the BUILT gate OBJ (ledger 0052).")
    ap.add_argument("project", type=Path)
    ap.add_argument("--layout", required=True)
    ap.add_argument("--ai", type=Path, help="default <project>/ai/<layout>/fast_lane.ai")
    ap.add_argument("--obj", type=Path, help="default <project>/data/track.<layout>.obj")
    ap.add_argument("--out", type=Path, help="default <project>/data/ai_verify.<layout>.json")
    ap.add_argument("--baseline", type=Path, help="the line this one replaces: V6, every corner keeps >= box_keep_min "
                                                    "x its radius")
    a = ap.parse_args(argv)
    aip = a.ai or a.project / "ai" / a.layout / "fast_lane.ai"
    objp = a.obj or a.project / "data" / f"track.{a.layout}.obj"
    outp = a.out or a.project / "data" / f"ai_verify.{a.layout}.json"
    th = thresholds(a.project)
    ai = read_ai(aip)
    walls = road = None
    if objp.exists():
        ob = read_gate_obj(objp)
        walls, road = WallIndex(ob.wall_segs), RoadSurface(ob)
        built = {"obj": str(objp), "header": ob.header, "wall_segments": len(ob.wall_segs), "road_tris": len(ob.road_tris)}
    else:
        built = {"obj": str(objp), "missing": True}
    m = measure(ai, walls=walls, road=road, th=th)
    if a.baseline is not None:
        m["v6"] = dict(corners_vs_baseline(ai, read_ai(a.baseline), th), baseline=str(a.baseline))
    fails = judge(m, th)
    rep = {"gate": "verify_ai_line (ledger 0052)", "layout": a.layout, "ai": str(aip), "built": built,
           "thresholds": th, "measured": m, "fail": fails, "ok": not fails}
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(rep, indent=1), encoding="utf-8")
    v2, v3, v4 = m.get("v2", {}), m["v3"], m.get("v4", {})
    print(f"verify_ai_line {a.layout}: wall min {v2.get('min_m')} m, under {th['wall_band_m']} m {v2.get('under_band_frac')}; "
          f"spurious dips {v3['dip_pts']}, flips {v3['flips_per_km']}/km; sides past a wall {v4.get('overreach_pts')}; "
          f"min radius {m['v5']['min_radius_m']} m; "
          + (f"corners keep >= {m['v6']['min_ratio']} x the baseline's; " if "v6" in m else "")
          + f"lap est {v3['lap_s_car_scale']} s (mu 1.0) -> {outp}")
    for r in fails:
        print(f"  FAIL {r}")
    print("  PASS" if not fails else f"  FAIL ({len(fails)})")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())

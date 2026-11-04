"""Apply real-world Prodrive Scan evidence to the built geometry.

The bare-earth USGS heightfield is accurate on open ground but wrong where the *road deck* differs from
the ground it sampled — bridges/overpasses, embankments, cuts. The capture measured the actual road
surface the car drove, so where it CONFIDENTLY diverges from the heightfield we trust the capture; where
they agree (the common case) we keep the cleaner, denser heightfield. The result: real elevation at the
spots the heightfield can't know about, without injecting GPS noise into the 80%+ that's already right.

Consumed by build_mesh (the driven kn5 road) and build_env (so terrain conforms to the corrected road),
both guarded: no ``source/realworld_capture.json`` → the input is returned unchanged (reproducibility).
Pure stdlib. See [[companion-app-plan]].
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

CAPTURE_NAME = "realworld_capture.json"

Vertex = tuple[float, float, float]


def load_capture(project_dir: str | Path) -> dict[str, Any] | None:
    """Return the committed capture evidence if it exists and carries stations, else None."""
    p = Path(project_dir) / "source" / CAPTURE_NAME
    if not p.exists():
        return None
    doc = json.loads(p.read_text(encoding="utf-8"))
    return doc if doc.get("stations") else None


def use_capture_elevation(project_dir: str | Path) -> bool:
    """Whether to apply the captured road-surface elevation to the centerline Y.

    The phone's GPS/baro altitude is too noisy on flat terrain to trust on its own. ``corrected_elevation``
    now reins it in (transient-spike rejection + a flat-terrain noise gate + corrections allowed only at
    declared bridge/overpass crossings), so it's safe to leave on. A track opts out with
    ``capture.use_elevation = false`` in track.config.json, and the road then follows the clean USGS 3DEP
    heightfield everywhere. Captured TEXTURES + lateral evidence are unaffected. Defaults True so tracks
    without the key keep the guarded behaviour. See [[ac-fallthrough-real-cause]]."""
    cfg = Path(project_dir) / "track.config.json"
    if not cfg.exists():
        return True
    return bool(json.loads(cfg.read_text(encoding="utf-8")).get("capture", {}).get("use_elevation", True))


def bridge_spans(project_dir: str | Path) -> list[tuple[float, float]]:
    """Declared deck crossings from ``capture.bridges`` in track.config.json, as ``[(center_m, len_m), …]``
    in lap-station metres (the same convention as ``road_profile.dips``).

    These are the ONLY places ``corrected_elevation`` permits a metre-scale lift: a real bridge/overpass
    keeps a level deck while the bare-earth DEM dips into the creek/underpass below it. Everywhere else the
    USGS heightfield is ground truth and the captured altitude is treated as noise. ``[]`` (no key) → no
    crossings, so the capture can only nudge the road sub-metre. See [[companion-app-plan]]."""
    cfg = Path(project_dir) / "track.config.json"
    if not cfg.exists():
        return []
    raw = json.loads(cfg.read_text(encoding="utf-8")).get("capture", {}).get("bridges", []) or []
    return [(float(b["center_m"]), float(b["len_m"])) for b in raw]


def _hampel(stations: list[float], alts: list[float], *, half_m: float, thr_m: float) -> tuple[list[float], int]:
    """Robust transient-spike rejection on the captured altitude series (a Hampel filter).

    A station whose altitude deviates from the MEDIAN of its ``±half_m`` neighbours by more than ``thr_m``
    is a transient — the phone physically dropped, a GPS/baro glitch — not real road grade (gentle terrain
    can't move >``thr_m`` over <``half_m``). Such a station is replaced with the local median. A genuine
    sustained deck (a level bridge over a creek) reads smoothly and stays the local majority, so it is NOT
    flagged. Returns (cleaned_alts, n_replaced)."""
    m = len(stations)
    out = alts[:]
    n_replaced = 0
    for i in range(m):
        lo = hi = i
        while lo > 0 and stations[i] - stations[lo - 1] <= half_m:
            lo -= 1
        while hi < m - 1 and stations[hi + 1] - stations[i] <= half_m:
            hi += 1
        win = sorted(alts[lo:hi + 1])
        med = win[len(win) // 2]
        if abs(alts[i] - med) > thr_m:
            out[i] = med
            n_replaced += 1
    return out, n_replaced


def corrected_elevation(
    points_xyz: list[Vertex],
    capture: dict[str, Any],
    *,
    bridges: list[tuple[float, float]] = (),   # declared [(center_m, len_m)] deck crossings — the ONLY
    #                                            places a metre-scale lift is allowed (positive signal)
    min_n: int = 8,            # only trust stations driven on enough passes (rejects 1-pass GPS spikes)
    outlier_win_m: float = 50.0,   # Hampel window for transient-spike rejection on the captured altitude
    outlier_m: float = 2.0,        # |alt − local median| above this is a transient (phone-fell/GPS glitch)
    blend_lo: float = 1.0,     # |diff| below this → keep heightfield (within its accuracy + GPS noise)
    blend_hi: float = 3.0,     # |diff| above this → fully trust the captured road surface
    relief_win_m: float = 80.0,    # window for local bare-earth relief — flat ⇒ divergence is GPS noise
    relief_lo: float = 1.0,        # relief below this → gate the correction to 0 (terrain is flat)
    relief_hi: float = 3.0,        # relief above this → terrain has real vertical structure
    max_correction_m: float = 6.0,    # cap INSIDE a declared bridge (covers Sand Creek's deepest crossing,
    #                                   the ~7 m-deep E 56th creek bed; only applies on trusted crossings)
    off_bridge_cap_m: float = 0.5,    # cap everywhere else: sub-metre, so noise can't move the road deck
    bridge_ramp_m: float = 25.0,      # raised-cosine taper of the cap at a bridge's edges
    max_gap_m: float = 30.0,   # don't interpolate captured elevation across an uncovered stretch
    smooth_passes: int = 30,
) -> tuple[list[Vertex], dict[str, Any]]:
    """Centerline with road-surface elevation corrected from the capture (Y only; X/Z untouched).

    The bare-earth USGS heightfield is ground truth on open ground; the phone's GPS/baro altitude is too
    noisy on flat terrain to trust on divergence alone (it injected fake metre-scale bumps and phone-fell
    dips). So the correction is reined in three ways:

      (a) transient spikes in the captured altitude are rejected (``_hampel``) — the phone dropping, a GPS
          glitch — before anything else;
      (b) a **flat-terrain noise gate**: where the bare earth is locally flat (low ``relief``), divergence
          is GPS noise and the correction is gated toward 0. A metre-scale lift is permitted ONLY inside a
          **declared bridge span** (``bridges``) — the positive signal that a level deck really does ride
          over a dipping bare earth. Off a declared crossing the correction is hard-capped sub-metre, so
          the road follows the clean DEM;
      (c) a small ``max_correction_m`` and strong smoothing.

    Confidence blends on |captured − heightfield| (after removing the constant car-height/GPS offset).
    Because the correction is 0 outside coverage it ramps cleanly to nothing at the driven-section edges.
    Returns (new_points, stats).
    """
    pts = [tuple(p) for p in points_xyz]
    n = len(pts)
    none_stats = {"n_corrected": 0, "max_corr_m": 0.0, "coverage_pts": 0, "offset_m": 0.0,
                  "n_outliers": 0, "max_offbridge_m": 0.0}
    if n < 2:
        return pts, none_stats

    ev = sorted((s["station_m"], s["alt_m"]) for s in capture["stations"]
                if s.get("alt_m") is not None and s.get("n", 0) >= min_n)
    if len(ev) < 2:
        return pts, none_stats
    ev_st = [e[0] for e in ev]
    ev_al = [e[1] for e in ev]
    # (a) reject transient altitude spikes (phone-fell / GPS glitches) before interpolating
    ev_al, n_outliers = _hampel(ev_st, ev_al, half_m=outlier_win_m / 2.0, thr_m=outlier_m)

    # arc length along the centerline (the same station convention the capture is keyed on)
    S = [0.0]
    for i in range(1, n):
        S.append(S[-1] + math.hypot(pts[i][0] - pts[i - 1][0], pts[i][2] - pts[i - 1][2]))

    def cap_alt_at(st: float) -> float | None:
        if st < ev_st[0] or st > ev_st[-1]:
            return None
        lo, hi = 0, len(ev_st) - 1
        while hi - lo > 1:
            m = (lo + hi) // 2
            if ev_st[m] <= st:
                lo = m
            else:
                hi = m
        if ev_st[hi] - ev_st[lo] > max_gap_m:   # bracketing stations too far apart → uncovered gap
            return None
        t = (st - ev_st[lo]) / max(1e-9, ev_st[hi] - ev_st[lo])
        return ev_al[lo] + t * (ev_al[hi] - ev_al[lo])

    cap_y = [cap_alt_at(S[i]) for i in range(n)]
    hf_y = [pts[i][1] for i in range(n)]
    deltas = sorted(cap_y[i] - hf_y[i] for i in range(n) if cap_y[i] is not None)
    if not deltas:
        return pts, none_stats
    offset = deltas[len(deltas) // 2]   # median car-height/GPS-bias offset → keep heightfield baseline

    # (b) local bare-earth relief over ±relief_win_m/2 (flat ⇒ the heightfield is trustworthy, divergence
    # is noise; real vertical structure ⇒ the capture may carry signal). Window in station-metres.
    rh = relief_win_m / 2.0
    relief = [0.0] * n
    for i in range(n):
        lo = hi = i
        while lo > 0 and S[i] - S[lo - 1] <= rh:
            lo -= 1
        while hi < n - 1 and S[hi + 1] - S[i] <= rh:
            hi += 1
        seg = hf_y[lo:hi + 1]
        relief[i] = max(seg) - min(seg)

    def _ramp(x: float, a: float, b: float) -> float:
        return 0.0 if x <= a else 1.0 if x >= b else (x - a) / (b - a)

    def bridge_member(st: float) -> float:
        """1 inside a declared crossing, raised-cosine ramp to 0 over ``bridge_ramp_m`` past its edges."""
        best = 0.0
        for center, length in bridges:
            d = abs(st - center)
            half = length / 2.0
            if d <= half:
                mm = 1.0
            elif d >= half + bridge_ramp_m:
                mm = 0.0
            else:
                mm = 0.5 * (1.0 + math.cos(math.pi * (d - half) / bridge_ramp_m))
            best = max(best, mm)
        return best

    corr = [0.0] * n
    capm = [off_bridge_cap_m] * n
    for i in range(n):
        if cap_y[i] is None:
            continue
        d = (cap_y[i] - offset) - hf_y[i]
        w_blend = _ramp(abs(d), blend_lo, blend_hi)
        mb = bridge_member(S[i])
        # a correction needs EITHER real terrain relief OR a declared crossing to open the gate; the cap
        # then keeps anything off a declared crossing sub-metre (only the bridge earns a metre-scale lift).
        gate = max(_ramp(relief[i], relief_lo, relief_hi), mb)
        capm[i] = off_bridge_cap_m + mb * (max_correction_m - off_bridge_cap_m)
        corr[i] = max(-capm[i], min(capm[i], w_blend * gate * d))

    for _ in range(smooth_passes):     # smooth + auto-ramp to 0 at the coverage edges
        nc = corr[:]
        for i in range(1, n - 1):
            nc[i] = 0.25 * corr[i - 1] + 0.5 * corr[i] + 0.25 * corr[i + 1]
        corr = nc
    for i in range(n):                 # re-clamp: smoothing can't push an off-bridge point over its cap
        corr[i] = max(-capm[i], min(capm[i], corr[i]))

    new_pts = [(pts[i][0], pts[i][1] + corr[i], pts[i][2]) for i in range(n)]
    max_offbridge = max((abs(corr[i]) for i in range(n) if bridge_member(S[i]) < 0.01), default=0.0)
    stats = {
        "n_corrected": sum(1 for c in corr if abs(c) > 0.05),
        "max_corr_m": round(max((abs(c) for c in corr), default=0.0), 2),
        "coverage_pts": len(deltas),
        "offset_m": round(offset, 2),
        "n_outliers": n_outliers,
        "max_offbridge_m": round(max_offbridge, 2),
    }
    return new_pts, stats


def level_bridge_decks(points_xyz: list[Vertex], bridges: list[tuple[float, float]],
                       *, ramp_m: float = 30.0) -> list[Vertex]:
    """Ride a real bridge as a LEVEL/SMOOTH deck over the dipping bare earth below it (Y only).

    The capture-based lift can't help where the phone data is noisy (Sand Creek's creek — the phone
    dropped there), so the road follows the bare-earth DEM straight into the creek bed (a steep dive,
    the 'corkscrew narnia'). A declared bridge is a positive geometric fact: over its span the deck is a
    straight interpolation between the APPROACH heights just outside the span, blended in with a
    raised-cosine ramp so it meets the grade smoothly. Result: the road decks over the creek accurately
    instead of diving into it. No capture needed.

    Station frame: arc length along ``points_xyz`` as build_mesh passes them, the DRAFT line
    (centerline.local.json), before corner rounding and smoothing. The finished line is shorter (Sand Creek:
    14 m by the E 56th bridge, 23 m by the lap's end), and the gates read the same ``center_m``/``len_m`` on
    the finished line. A measured deck (``profile_m``, apply_deck_profiles) is keyed to the finished line."""
    n = len(points_xyz)
    if n < 2 or not bridges:
        return [tuple(p) for p in points_xyz]
    pts = [list(p) for p in points_xyz]
    S = [0.0]
    for i in range(1, n):
        S.append(S[-1] + math.hypot(pts[i][0] - pts[i - 1][0], pts[i][2] - pts[i - 1][2]))
    BANK_SEEK_M = 80.0   # how far outside the span to look for the true bank crest
    for center, length in bridges:
        half = length / 2.0
        # Anchor the deck on the BANK CRESTS, not at a fixed offset: the bare-earth valley is often
        # wider than the declared span (Sand Creek's at 56th is ~225 m wide), so a fixed 30 m anchor
        # lands partway down the dive and the "level deck" gets built 2-3 m into the hole, with a
        # dive in and a pop-out ramp at each end (the '56th dip + rolling hill').
        la, lb = center - half, center + half
        ia = [i for i in range(n) if la - BANK_SEEK_M <= S[i] <= la]
        ib = [i for i in range(n) if lb <= S[i] <= lb + BANK_SEEK_M]
        if not ia or not ib:
            ia = [min(range(n), key=lambda i: abs(S[i] - (la - ramp_m)))]
            ib = [min(range(n), key=lambda i: abs(S[i] - (lb + ramp_m)))]
        i_a = max(ia, key=lambda i: pts[i][1])
        i_b = max(ib, key=lambda i: pts[i][1])
        a, b, ya, yb = S[i_a], S[i_b], pts[i_a][1], pts[i_b][1]
        for i in range(n):
            if a <= S[i] <= b:
                # straight crest-to-crest deck: endpoints sit ON raw ground, so no blend — a blend
                # let the raw valley bleed a 0.9 m dip back in between span end and crest. The
                # centerline smoothing pass rounds the small grade breaks at the crests.
                pts[i][1] = ya + (yb - ya) * (S[i] - a) / max(1e-9, b - a)
    return [tuple(p) for p in pts]


DECK_PROFILE_RAMP_M = 20.0   # [invented] raised-cosine hand-back to the road outside a measured profile


def deck_profiles(cfg: dict) -> list[dict[str, Any]]:
    """The MEASURED deck profiles declared on ``capture.bridges[].profile_m`` (opt-in, per bridge), as
    ``[{"name", "profile": [(station_m, height_m), ...], "ramp_m"}]``. Bridges without one are left out, and
    a config with none returns ``[]``, which every caller treats as "change nothing".

    ``profile_m`` is ``[[d_m, height_m], ...]``: ``d_m`` is metres from the bridge's START, ``center_m -
    len_m / 2``, along the FINISHED line (the corner-rounded, smoothed line build_mesh sweeps the road over
    and writes to ``data/finished_centerline.json``, the frame the gates, the lidar crossfall and the
    road_profile dips are keyed to), strictly increasing, negative before the start (an approach point).
    Keyed to the start, a line change re-keys the whole deck by moving ``center_m``. Heights are absolute, in
    the elevation source's vertical datum (``y + origin elev_m``), as a source-lidar survey reads them: they
    are the real road's and do not change with the line. ``profile_ramp_m`` (default DECK_PROFILE_RAMP_M) is
    how far outside each end the road is eased to meet the profile. The returned ``profile`` is in absolute
    finished-line stations. Note level_bridge_decks reads ``center_m``/``len_m`` on the draft line
    (centerline.local.json), not this one; see that function."""
    out = []
    for b in ((cfg.get("capture") or {}).get("bridges") or []):
        prof = b.get("profile_m")
        if not prof:
            continue
        if "center_m" not in b or "len_m" not in b:
            raise ValueError(f"capture.bridges {b.get('name', '?')}: profile_m is measured from the bridge's start "
                             f"(center_m - len_m / 2): it needs center_m and len_m")
        start = float(b["center_m"]) - float(b["len_m"]) / 2.0
        pts = [(start + float(d), float(h)) for d, h in prof]
        if len(pts) < 2 or any(pts[k + 1][0] <= pts[k][0] for k in range(len(pts) - 1)):
            raise ValueError(f"capture.bridges {b.get('name', '?')}: profile_m needs >= 2 [metres from start, height] "
                             f"points, strictly increasing")
        out.append({"name": b.get("name", ""), "start_m": start, "profile": pts,
                    "ramp_m": float(b.get("profile_ramp_m", DECK_PROFILE_RAMP_M))})
    return out


def apply_deck_profiles(points_xyz: list[Vertex], profiles: list[dict[str, Any]], *,
                        origin_elev_m: float) -> list[Vertex]:
    """Lay each measured deck profile onto the finished line (Y only; X/Z untouched).

    level_bridge_decks holds a deck as ONE straight grade between its bank crests, because the bare-earth
    DEM has no deck in it. Where the source lidar has the deck itself (ASPRS class 17), the deck is not
    straight: Sand Creek's E 56th deck over the creek is crowned 0.29 m and sits 0.41 m (median) above the
    straight grade (ledger 0068). Inside ``[first, last]`` profile station the road takes the profile,
    linearly between its points; outside, the difference at that end eases back to the road it had over
    ``ramp_m`` with a raised cosine, so there is no step and no grade break at the hand-over.

    Stations are horizontal arc length along ``points_xyz`` from point 0. On a closed lap (L13: the first
    vertex repeated last) distances wrap, so a profile near the seam eases across it and the duplicate
    closing vertex gets exactly what vertex 0 gets. ``profiles == []`` returns the points unchanged."""
    pts = [tuple(p) for p in points_xyz]
    n = len(pts)
    if n < 2 or not profiles:
        return pts
    S = [0.0]
    for i in range(1, n):
        S.append(S[-1] + math.hypot(pts[i][0] - pts[i - 1][0], pts[i][2] - pts[i - 1][2]))
    lap = S[-1]
    closed = (abs(pts[0][0] - pts[-1][0]) < 1e-6 and abs(pts[0][1] - pts[-1][1]) < 1e-6
              and abs(pts[0][2] - pts[-1][2]) < 1e-6)

    def y_at(s: float) -> float:
        import bisect
        k = min(max(bisect.bisect_right(S, s), 1), n - 1)
        t = (s - S[k - 1]) / max(1e-12, S[k] - S[k - 1])
        return pts[k - 1][1] + t * (pts[k][1] - pts[k - 1][1])

    def h_at(prof: list[tuple[float, float]], s: float) -> float:
        for k in range(1, len(prof)):
            if s <= prof[k][0]:
                (s0, h0), (s1, h1) = prof[k - 1], prof[k]
                return h0 + (h1 - h0) * (s - s0) / (s1 - s0)
        return prof[-1][1]

    ys = [p[1] for p in pts]
    for pr in profiles:
        prof, ramp = pr["profile"], max(1e-6, pr["ramp_m"])
        a, b = prof[0][0], prof[-1][0]
        d_a = (prof[0][1] - origin_elev_m) - y_at(a % lap if closed else a)    # lift wanted at each end
        d_b = (prof[-1][1] - origin_elev_m) - y_at(b % lap if closed else b)
        for i in range(n):
            cands = (S[i], S[i] - lap, S[i] + lap) if closed else (S[i],)
            inside = next((s for s in cands if a <= s <= b), None)
            if inside is not None:
                ys[i] = h_at(prof, inside) - origin_elev_m
                continue
            gap_a = min((a - s for s in cands if s < a), default=math.inf)    # before the first point
            gap_b = min((s - b for s in cands if s > b), default=math.inf)    # after the last
            if gap_a <= gap_b and gap_a < ramp:
                ys[i] += d_a * 0.5 * (1.0 + math.cos(math.pi * gap_a / ramp))
            elif gap_b < ramp:
                ys[i] += d_b * 0.5 * (1.0 + math.cos(math.pi * gap_b / ramp))
    return [(pts[i][0], ys[i], pts[i][2]) for i in range(n)]


def cap_grade(points_xyz: list[Vertex], *, max_grade: float = 0.06) -> list[Vertex]:
    """Clamp the along-road slope so no stretch exceeds ``max_grade`` — kills residual steep spikes that
    launch the car ('narnia'), turning a too-steep section into a drivable grade. Y only, forward pass."""
    n = len(points_xyz)
    if n < 2:
        return [tuple(p) for p in points_xyz]
    pts = [list(p) for p in points_xyz]
    for i in range(1, n):
        ds = math.hypot(pts[i][0] - pts[i - 1][0], pts[i][2] - pts[i - 1][2])
        cap = max_grade * ds
        dy = pts[i][1] - pts[i - 1][1]
        pts[i][1] = pts[i - 1][1] + max(-cap, min(cap, dy))
    return [tuple(p) for p in pts]

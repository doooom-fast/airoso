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


def _md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def run(proj: Path, offline: bool = False) -> dict | None:
    data = proj / "data"
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    decks = (cfg.get("road_datum") or {}).get("decks") or []
    if not decks:
        print("[deck] no road_datum.decks declared — nothing to do")
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
    for d in decks:
        w0, w1 = (float(v) for v in d["window_m"])
        a, b = (float(v) for v in d["deck_m"])
        if not (w0 + BLEND_M <= a < b <= w1 - BLEND_M):
            raise SystemExit(f"[deck] {d['name']}: deck {d['deck_m']} must sit inside window {d['window_m']} "
                             f"by {BLEND_M} m")
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

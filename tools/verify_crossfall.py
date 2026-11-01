"""The roll-rate gate on a track's crossfall (Lariat V3, ledger 0048, V3-PLAN P2 step 4 / P5).

Reads ``data/crossfall.json`` (``scripts.elevation.crossfall``; the footprint mode writes each half of the section
as ``left_pct`` / ``right_pct``, + = that half's left side higher; a legacy file has only ``bank_rad``, read as one
plane) and judges both halves round the lap with ``scripts.elevation.crossfall.roll_rate_check``:
  (a) within any 30 m the tilt changes by <= 4 %                         [invented, V3-PLAN P5]
  (b) no swing from >= +3 % to <= -3 % (or back) within 30 m: 0          [invented, V3-PLAN P5]
It also requires the file's own record to be honest: a ``status`` (``estimated`` until a 3DEP source-lidar
sample agrees), stations ascending inside [0, lap), and covering the lap (no gap over 2 steps, the seam
included: L13). It reports, without gating, the stations where the inside half tilts down into a curve tighter
than 100 m by more than the construction standard's 2 % (A6: nothing is banked).

This judges the DATA the road will be built from. The built file gets the same rules on its swept sections in
the Drive-1 gate set (P5), when the underlay exists: L5, a gate on the data that placed the road is a precondition,
not the verdict.

Writes ``data/crossfall_gate.json``. Exit 0 PASS, 1 FAIL, 2 no file.

    python tools/verify_crossfall.py <project-dir>
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
from scripts.elevation.crossfall import (ROLL_MAX_CHANGE_PCT, ROLL_SWING_PCT, ROLL_WINDOW_M,  # noqa: E402
                                         roll_rate_check)


def judge(cf: dict, lap_m: float | None = None) -> dict:
    st = [float(s) for s in cf["station_m"]]
    if "left_pct" in cf and "right_pct" in cf:
        halves = {"left": [float(v) for v in cf["left_pct"]], "right": [float(v) for v in cf["right_pct"]]}
    else:
        plane = [100.0 * math.tan(float(b)) for b in cf["bank_rad"]]
        halves = {"plane": plane}
    n = len(st)
    lap = float(lap_m if lap_m is not None else (cf.get("summary") or {}).get("lap_m") or (st[-1] + (st[1] - st[0])))
    problems = []
    if not cf.get("status"):
        problems.append("no status (a crossfall is 'estimated' until a source-lidar sample agrees)")
    if any(b <= a for a, b in zip(st, st[1:])) or st[0] < 0 or st[-1] >= lap:
        problems.append("stations are not ascending inside [0, lap)")
    step = min(b - a for a, b in zip(st, st[1:])) if n > 1 else 0.0
    gaps = [(a, b) for a, b in zip(st, st[1:]) if b - a > 2 * step + 1e-6]
    seam_gap = lap - st[-1] + st[0]
    if seam_gap > 2 * step + 1e-6:
        gaps.append((st[-1], st[0] + lap))
    if gaps:
        problems.append(f"{len(gaps)} gap(s) over 2 steps, first {gaps[0]}")
    res = {}
    for name, series in halves.items():
        if len(series) != n:
            problems.append(f"{name}: {len(series)} values for {n} stations")
            continue
        g = roll_rate_check(st, series, lap, closed=True)
        res[name] = {"change_fail_stations": len(g["change_fail"]), "swing_fail_stations": len(g["swing_fail"]),
                     "swings": g["swings"], "worst_change_pct": g["worst_change_pct"], "worst_at_m": g["worst_at_m"],
                     "first_change_fail_m": [round(st[i], 1) for i in g["change_fail"][:10]],
                     "first_swing_fail_m": [round(st[i], 1) for i in g["swing_fail"][:10]]}
        if g["change_fail"]:
            problems.append(f"{name}: {len(g['change_fail'])} station(s) where the tilt changes > "
                            f"{ROLL_MAX_CHANGE_PCT:g} % within {ROLL_WINDOW_M:g} m (worst {g['worst_change_pct']} % "
                            f"at st {g['worst_at_m']})")
        if g["swing_fail"]:
            problems.append(f"{name}: {g['swings']} swing(s) from >= +{ROLL_SWING_PCT:g} % to <= -{ROLL_SWING_PCT:g} % "
                            f"within {ROLL_WINDOW_M:g} m")
    banked = (cf.get("summary") or {}).get("final", {}).get("banked_into_curve_stations")
    return {"gate": "roll rate (V3-PLAN P2 step 4 / P5)", "status_of_file": cf.get("status"),
            "rules": {"max_change_pct_per_window": ROLL_MAX_CHANGE_PCT, "window_m": ROLL_WINDOW_M,
                      "swing_pct": ROLL_SWING_PCT, "flags": "[invented] both (fleet/GATES-CHANGELOG.md)"},
            "stations": n, "lap_m": round(lap, 1), "halves": res,
            "banked_into_curve_stations_reported": banked,
            "problems": problems, "fail": bool(problems)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python tools/verify_crossfall.py")
    ap.add_argument("project_dir")
    a = ap.parse_args(argv)
    data = Path(a.project_dir) / "data"
    p = data / "crossfall.json"
    if not p.exists():
        print(f"[crossfall gate] no {p}")
        return 2
    cf = json.loads(p.read_text(encoding="utf-8"))
    lap = None
    lc = data / "centerline.local.json"
    if lc.exists():
        pts = json.loads(lc.read_text(encoding="utf-8"))["points_xyz_m"]
        lap = sum(math.hypot(pts[i][0] - pts[i - 1][0], pts[i][2] - pts[i - 1][2]) for i in range(1, len(pts)))
    r = judge(cf, lap)
    (data / "crossfall_gate.json").write_text(json.dumps(r, indent=1), encoding="utf-8")
    for name, h in r["halves"].items():
        print(f"[crossfall gate] {name:5s}: worst change {h['worst_change_pct']} % / {ROLL_WINDOW_M:g} m at st "
              f"{h['worst_at_m']}; {h['change_fail_stations']} change fail, {h['swings']} swing(s)")
    print(f"[crossfall gate] file status: {r['status_of_file']}; banked-into-curve stations (reported): "
          f"{r['banked_into_curve_stations_reported']}")
    for q in r["problems"]:
        print(f"  FAIL {q}")
    print(f"[crossfall gate] {'FAIL' if r['fail'] else 'PASS'} -> {data / 'crossfall_gate.json'}")
    return 1 if r["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())

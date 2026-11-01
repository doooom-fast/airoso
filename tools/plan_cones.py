"""Plan the corner cones from the lap's own curvature and print the declaration tools/author_bespoke_blend.py places.

DOSSIER section 5 (Exotics Racing): traffic cones "at the braking point, apex and exit of every corner" [S19]. NAIP does not
resolve a cone, so WHERE is a rule, not a measurement, and the rule is written here: a corner is a run of the centreline
whose curvature (over a +-CURV_WINDOW_M chord) stays above CORNER_MIN_CURV; the apex cone stands on the inside where half
the corner's turning is done, the exit cone on the outside at the corner's end, and the brake cone on the outside
BRAKE_BACK_M before its start, unless the corner before it ends inside that distance (an S has no braking zone of its own).
Corners closer than MERGE_M merge into one. Every number here is [invented].

    PYTHONUTF8=1 python tools/plan_cones.py <project>          # prints the JSON for scenery.bespoke.cones.stations

The frame is the draft's: data/centerline.local.json, x = E, y = up, z = N. side "L" / "R" is left / right of travel.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

CURV_WINDOW_M = 12.0
CORNER_MIN_CURV = 1.0 / 90.0   # tighter than 90 m radius
MIN_CORNER_M = 15.0            # a shorter run is a wiggle in the trace, not a corner
MERGE_M = 25.0
BRAKE_BACK_M = 40.0


def arc_lengths(pts):
    s = [0.0]
    for a, b in zip(pts, pts[1:]):
        s.append(s[-1] + math.hypot(b[0] - a[0], b[2] - a[2]))
    return s


def signed_curvature(pts):
    """per point, positive = turning left, over a chord of +-CURV_WINDOW_M along the closed lap"""
    n = len(pts)
    seg = sum(math.hypot(pts[(i + 1) % n][0] - pts[i][0], pts[(i + 1) % n][2] - pts[i][2]) for i in range(n)) / n
    k = max(1, int(round(CURV_WINDOW_M / seg)))
    out = []
    for i in range(n):
        a, b, c = pts[(i - k) % n], pts[i], pts[(i + k) % n]
        ux, uz = b[0] - a[0], b[2] - a[2]
        vx, vz = c[0] - b[0], c[2] - b[2]
        lu, lv = math.hypot(ux, uz) or 1e-9, math.hypot(vx, vz) or 1e-9
        turn = math.atan2(ux * vz - uz * vx, ux * vx + uz * vz)
        out.append(turn / ((lu + lv) / 2.0))
    return out


def corners(pts):
    """[(start_i, peak_i, end_i, sign)] in lap order; a run wrapping the seam is kept whole by starting the scan on a straight"""
    curv = signed_curvature(pts)
    n = len(pts)
    start = next((i for i in range(n) if abs(curv[i]) < CORNER_MIN_CURV), 0)
    order = [(start + i) % n for i in range(n)]
    s = arc_lengths(pts)
    total = s[-1] + math.hypot(pts[0][0] - pts[-1][0], pts[0][2] - pts[-1][2])

    def dist(a, b):
        return (s[b] - s[a]) % total
    runs = []
    cur = None
    for i in order:
        hot = abs(curv[i]) >= CORNER_MIN_CURV
        if hot and cur is not None and (curv[i] > 0) == cur["sign"]:
            cur["end"] = i
            if abs(curv[i]) > abs(curv[cur["peak"]]):
                cur["peak"] = i
        elif hot:
            if cur is not None:
                runs.append(cur)
            cur = {"start": i, "end": i, "peak": i, "sign": curv[i] > 0}
        elif cur is not None:
            runs.append(cur)
            cur = None
    if cur is not None:
        runs.append(cur)
    merged = []
    for r in runs:
        if merged and merged[-1]["sign"] == r["sign"] and dist(merged[-1]["end"], r["start"]) < MERGE_M:
            m = merged[-1]
            m["end"] = r["end"]
            if abs(curv[r["peak"]]) > abs(curv[m["peak"]]):
                m["peak"] = r["peak"]
        else:
            merged.append(dict(r))
    kept = [r for r in merged if dist(r["start"], r["end"]) >= MIN_CORNER_M]
    return kept, s, total, curv


def half_turn(r, curv, n):
    """the index in the run ``r`` where half of its turning is done (a curvature peak sits wherever the trace wiggles)"""
    i, idx = r["start"], []
    while True:
        idx.append(i)
        if i == r["end"]:
            break
        i = (i + 1) % n
    total = sum(abs(curv[j]) for j in idx)
    acc = 0.0
    for j in idx:
        acc += abs(curv[j])
        if acc >= total / 2.0:
            return j
    return r["peak"]


def stations(pts):
    kept, s, total, curv = corners(pts)
    out = []
    for k, r in enumerate(kept, 1):
        inside, outside = ("L", "R") if r["sign"] else ("R", "L")
        gap = (s[r["start"]] - s[kept[k - 2]["end"]]) % total
        if len(kept) == 1 or gap >= BRAKE_BACK_M:
            out.append({"corner": k, "role": "brake", "s": round((s[r["start"]] - BRAKE_BACK_M) % total, 1), "side": outside})
        out.append({"corner": k, "role": "apex", "s": round(s[half_turn(r, curv, len(pts))], 1), "side": inside})
        out.append({"corner": k, "role": "exit", "s": round(s[r["end"]], 1), "side": outside})
    return out, [{"corner": k, "s0": round(s[r["start"]], 1), "s1": round(s[r["end"]], 1),
                  "radius_m": round(1.0 / abs(curv[r["peak"]]), 1), "turn": "L" if r["sign"] else "R"}
                 for k, r in enumerate(kept, 1)]


def main():
    data = json.loads((Path(sys.argv[1]) / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    st, rows = stations([tuple(p) for p in data["points_xyz_m"]])
    print(json.dumps(st))
    for r in rows:
        print("#", r, file=sys.stderr)


if __name__ == "__main__":
    main()

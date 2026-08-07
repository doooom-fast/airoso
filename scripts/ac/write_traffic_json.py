"""Generate a CSP traffic lane graph (``data/traffic.json``) from the engine's centerline.

Kevin, 2026-08-07: "2real traffic is far more interesting to me than track day or races." For a
street port the product is the street ALIVE — CSP's traffic system (the bundled Traffic Planner /
2REAL-style apps) drives a lane graph stored as ``traffic.json`` beside ``surfaces.ini``. Nobody
in the scene generates these from map data; we hold the real centerline and widths, so we do.

Format (verified two ways, 2026-08-07): the CSP tool's own serializer
(acc-lua-internal/included-tools/traffic: EditorMain.serializeData + EditorLane.encode) and a
production file (No Hesi 110: 100 lanes, ~36 m point spacing, rules.laneRoles). Shape:

    { "lanes": [ {"id", "name", "role" (1 Parking / 2 Secondary / 3 Main omitted / 4 Highway),
                  "priorityOffset", "loop", "params": [], "points": [[x,y,z], ...]} ],
      "intersections": [], "areas": [],
      "rules": {"laneRoles": [{name, priority, speedLimit} x4]} }

Direction is the point ORDER (each lane is one-way; a two-way road is two lanes in opposite
orders). Points are in the AC/kn5 world frame — z-mirrored from the engine frame, same flip the
dummies and the gate OBJ taught us. Right-hand traffic: each direction's lane sits to the RIGHT
of travel.

    python -m scripts.ac.write_traffic_json <project-dir> [--install <AC-track-dir>]
        [--spacing 25] [--role 2] [--lane-offset-frac 0.25]

v1 scope: one lane per direction along the main centerline, junction areas left to the in-game
editor. The lane graph only takes effect with a CSP traffic runner (bundled tool + its data pack,
or the 2REAL app) — the file is the track-side half of the contract.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
from pathlib import Path

DEFAULT_RULES = {"laneRoles": [
    {"name": "Parking", "priority": -8, "speedLimit": 40},
    {"name": "Secondary", "priority": -4, "speedLimit": 60},
    {"name": "Main", "priority": 0, "speedLimit": 80},
    {"name": "Highway", "priority": 4, "speedLimit": 90},
]}


def _resample(pts, widths, spacing, closed):
    n = len(pts)
    seg, total = [], 0.0
    for i in range(n if closed else n - 1):
        d = math.dist(pts[i], pts[(i + 1) % n])
        seg.append(d); total += d
    count = max(4, round(total / spacing))
    step = total / count
    out_p, out_w = [], []
    i, acc, tgt = 0, 0.0, 0.0
    for _ in range(count if closed else count + 1):
        while i < len(seg) and acc + seg[i] < tgt - 1e-9:
            acc += seg[i]; i += 1
        if i >= len(seg):
            out_p.append(list(pts[0] if closed else pts[-1])); out_w.append(widths[0] if closed else widths[-1])
        else:
            t = (tgt - acc) / seg[i] if seg[i] > 1e-12 else 0.0
            a, b = pts[i], pts[(i + 1) % n]
            out_p.append([a[k] + (b[k] - a[k]) * t for k in range(3)])
            wa, wb = widths[i], widths[(i + 1) % n]
            out_w.append(wa + (wb - wa) * t)
        tgt += step
    return out_p, out_w


def _offset_lane(pts, widths, frac, side, closed, min_m=1.6, max_m=4.5):
    """Offset each point laterally. side=+1 → right of travel (US traffic), in ENGINE frame."""
    n = len(pts)
    out = []
    for i in range(n):
        a = pts[(i - 1) % n] if (closed or i > 0) else pts[i]
        b = pts[(i + 1) % n] if (closed or i < n - 1) else pts[i]
        fx, fz = b[0] - a[0], b[2] - a[2]
        nrm = math.hypot(fx, fz) or 1.0
        rx, rz = fz / nrm, -fx / nrm            # right of travel in engine XZ (x=E, z=N)
        o = max(min_m, min(max_m, widths[i] * frac)) * side
        out.append([pts[i][0] + rx * o, pts[i][1], pts[i][2] + rz * o])
    return out


def build_traffic(pts, widths, *, closed: bool, spacing: float, role: int,
                  offset_frac: float) -> dict:
    pts, widths = _resample(pts, widths, spacing, closed)
    fwd = _offset_lane(pts, widths, offset_frac, +1, closed)
    # the reverse lane is the reversed traversal with its OWN right-of-travel offset; the output
    # of _offset_lane on the reversed polyline is already in that lane's driving order
    rev = _offset_lane(list(reversed(pts)), list(reversed(widths)), offset_frac, +1, closed)
    lanes = []
    for i, (name, lane_pts) in enumerate((("forward", fwd), ("reverse", rev))):
        # engine -> AC/kn5 world: z mirrors (same flip as dummies/gate OBJ)
        world = [[round(p[0], 3), round(p[1], 3), round(-p[2], 3)] for p in lane_pts]
        lanes.append({"id": i + 1, "name": name, "loop": closed,
                      "role": role if role != 3 else None,
                      "priorityOffset": 0, "params": [], "points": world})
    for ln in lanes:
        if ln["role"] is None:
            del ln["role"]
    return {"lanes": lanes, "intersections": [], "areas": [], "rules": DEFAULT_RULES}


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate CSP traffic.json from the centerline.")
    ap.add_argument("project", type=Path)
    ap.add_argument("--install", type=Path, help="AC track dir; writes <dir>/data/traffic.json")
    ap.add_argument("--spacing", type=float, default=25.0, help="lane point spacing m (No Hesi ~36)")
    ap.add_argument("--role", type=int, default=2, help="laneRole index (2=Secondary 60 km/h)")
    ap.add_argument("--lane-offset-frac", type=float, default=0.25,
                    help="lateral offset as fraction of road width (clamped 1.6..4.5 m)")
    args = ap.parse_args()

    src = args.project / "data" / "finished_centerline.json"
    j = json.loads(src.read_text(encoding="utf-8"))
    pts, widths = j["points_xyz_m"], j["widths_m"]
    closed = math.dist(pts[0], pts[-1]) < 1e-6
    if closed:
        pts, widths = pts[:-1], widths[:-1]      # L13

    traffic = build_traffic(pts, widths, closed=closed, spacing=args.spacing,
                            role=args.role, offset_frac=args.lane_offset_frac)
    out = args.project / "data" / "traffic.json"
    out.write_text(json.dumps(traffic), encoding="utf-8")
    npts = sum(len(l["points"]) for l in traffic["lanes"])
    print(f"{out}  ({len(traffic['lanes'])} lanes, {npts:,} points, "
          f"{'loop' if closed else 'point-to-point'})")
    if args.install:
        dst = args.install / "data" / "traffic.json"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(out, dst)
        print(f"  -> {dst}")


if __name__ == "__main__":
    main()

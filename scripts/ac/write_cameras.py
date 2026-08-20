"""Generate an AC TV-camera set (``data/cameras.ini``) from the racing line — REALISM R5.

Measured gap (fleet/reference/MEASURED.md §6): references ship 18–1,611 trackside cameras; every
k10 track ships **zero**, so replays and the F3 chase have nothing to cut to and the track reads
unfinished. The format is copied field-for-field from a Kunos set (ks_laguna_seca
data/cameras.ini, VERSION=3): fixed cameras with POSITION/FORWARD/UP, FOV bounds, and normalized
IN_POINT/OUT_POINT windows along the lap.

Placement: one camera per ~350 m of lap, standing 15 m to the right of the line and 6 m up,
aimed at the middle of its coverage window. Positions are written in the AC/kn5 world frame
(z mirrored from the engine frame — the same flip as the dummies, the AI line, and the lanes).

    python -m scripts.ac.write_cameras <project-dir> [--install <AC-track-dir>]
        [--spacing 350] [--side 15] [--height 6]
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
from pathlib import Path

CAM_TAIL = """MIN_FOV={min_fov}
MAX_FOV={max_fov}
IN_POINT={inp:.6f}
OUT_POINT={outp:.6f}
SHADOW_SPLIT0=10
SHADOW_SPLIT1=60
SHADOW_SPLIT2=450
NEAR_PLANE=1
FAR_PLANE=5000
MIN_EXPOSURE=0
MAX_EXPOSURE=10000
DOF_FACTOR=10
DOF_RANGE=10000
DOF_FOCUS=0
DOF_MANUAL=0
SPLINE=
SPLINE_ROTATION=0
FOV_GAMMA=0.5
SPLINE_ANIMATION_LENGTH=15
IS_FIXED=0
"""


def _vec(v):
    return f"{v[0]:.4f} ,{v[1]:.4f} ,{v[2]:.4f}"


def build_cameras(pts, widths, *, closed: bool, spacing: float, side: float,
                  height: float) -> str:
    n = len(pts)
    cum = [0.0]
    for i in range(1, n):
        cum.append(cum[-1] + math.dist(pts[i - 1], pts[i]))
    total = cum[-1] + (math.dist(pts[-1], pts[0]) if closed else 0.0)
    count = max(8, min(60, round(total / spacing)))

    def at_arc(arc):
        arc = arc % total if closed else min(max(arc, 0.0), total - 1e-6)
        lo = 0
        for i in range(n):
            if cum[i] <= arc:
                lo = i
            else:
                break
        return pts[lo], lo

    out = [f"[HEADER]\nVERSION=3\nCAMERA_COUNT={count}\nSET_NAME=K10 TV\n"]
    for k in range(count):
        a0, a1 = k / count * total, (k + 1) / count * total
        mid_arc = (a0 + a1) / 2
        target, ti = at_arc(mid_arc)
        # camera stands beside the line at the window middle, right of travel, raised
        tan_a, _ = at_arc(mid_arc - 4)
        tan_b, _ = at_arc(mid_arc + 4)
        fx, fz = tan_b[0] - tan_a[0], tan_b[2] - tan_a[2]
        nrm = math.hypot(fx, fz) or 1.0
        rx, rz = fz / nrm, -fx / nrm                    # right of travel, engine XZ
        off = max(side, widths[ti] / 2.0 + 6.0)
        cam = [target[0] + rx * off, target[1] + height, target[2] + rz * off]
        f = [target[0] - cam[0], target[1] - cam[1], target[2] - cam[2]]
        fl = math.sqrt(sum(x * x for x in f)) or 1.0
        f = [x / fl for x in f]
        # engine -> AC world: mirror z on position AND forward
        cam_w = (cam[0], cam[1], -cam[2])
        f_w = (f[0], f[1], -f[2])
        out.append(f"[CAMERA_{k}]\nNAME={k + 1}\nPOSITION={_vec(cam_w)}\n"
                   f"FORWARD={_vec(f_w)}\nUP=0 ,1 ,0\n"
                   + CAM_TAIL.format(min_fov=6, max_fov=42, inp=a0 / total, outp=a1 / total))
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate data/cameras.ini from the racing line.")
    ap.add_argument("project", type=Path)
    ap.add_argument("--install", type=Path)
    ap.add_argument("--spacing", type=float, default=350.0)
    ap.add_argument("--side", type=float, default=15.0)
    ap.add_argument("--height", type=float, default=6.0)
    args = ap.parse_args()

    j = json.loads((args.project / "data" / "finished_centerline.json").read_text(encoding="utf-8"))
    pts, widths = j["points_xyz_m"], j["widths_m"]
    closed = math.dist(pts[0], pts[-1]) < 1e-6
    if closed:
        pts, widths = pts[:-1], widths[:-1]             # L13
    ini = build_cameras(pts, widths, closed=closed, spacing=args.spacing,
                        side=args.side, height=args.height)
    out = args.project / "data" / "cameras.ini"
    out.write_text(ini, encoding="ascii")
    ncams = ini.count("[CAMERA_")
    print(f"{out}  ({ncams} cameras)")
    if args.install:
        dst = args.install / "data" / "cameras.ini"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(out, dst)
        print(f"  -> {dst}")


if __name__ == "__main__":
    main()
